# Terraform 운영 아키텍처

## 변경·권한·state 흐름

```mermaid
flowchart TB
    Developer[개발자] --> PR[GitHub Pull Request]
    PR --> Checks[Terraform checks]
    Checks --> Static[fmt · validate · terraform test<br/>Python 회귀 테스트]
    Static -. AWS 자격 증명 없음 .-> NoAWS[실제 AWS와 원격 state 접근 안 함]

    Operator[Terraform 운영자] -->|MFA 역할 전환| PlanRole[Plan Role]
    Operator -->|검토된 plan 적용| ApplyRole[Apply Role]
    PlanRole -->|state 읽기 · lock 관리| ProjectState[(Project state)]
    PlanRole -->|현재 상태 조회| Managed[AWS 관리 자원]
    ApplyRole -->|state 쓰기 · lock 관리| ProjectState
    ApplyRole -->|허용된 변경만 수행| Managed

    Emergency[비상 복구 운영자] -->|MFA 역할 전환| BootstrapRole[Bootstrap Admin Role]
    BootstrapRole -->|복구·관리| BootstrapState[(Bootstrap state)]
    BootstrapRole -->|복구·관리| TerraformIAM[Terraform IAM 역할]

    Team[팀원별 IAM 사용자] -->|MFA 역할 전환| TeamRole[Team Admin Role]
    TeamRole -->|일반 운영| AWSAccount[AWS 프로젝트 계정]
    TeamRole -. 보호 정책 .-> Guardrail[state · Terraform 역할 · 운영자 변경 차단]

    StateBucket[(S3 state 버킷<br/>버전 관리 · 암호화 · 잠금)]
    StateBucket --- BootstrapState
    StateBucket --- ProjectState

    classDef ci fill:#e8f1ff,stroke:#2563eb,color:#111827;
    classDef identity fill:#f3e8ff,stroke:#7e22ce,color:#111827;
    classDef state fill:#dcfce7,stroke:#15803d,color:#111827;
    classDef aws fill:#fff7ed,stroke:#c2410c,color:#111827;
    class Checks,Static,NoAWS ci;
    class Operator,PlanRole,ApplyRole,Emergency,BootstrapRole,Team,TeamRole identity;
    class StateBucket,BootstrapState,ProjectState state;
    class Managed,TerraformIAM,AWSAccount,Guardrail aws;
```

### 흐름 해석

1. Pull request에서는 AWS 접속 없이 코드 형식·구성·테스트만 검증
2. 운영자가 MFA로 Plan Role을 맡아 실제 자원과 state의 차이 확인
3. 검토한 변경만 Apply Role로 적용하고 project state 갱신
4. state 버킷이나 Terraform IAM 복구가 필요할 때만 Bootstrap Admin Role 사용
5. 팀원은 개인 IAM 사용자에서 MFA로 Team Admin Role을 맡아 일반 AWS 작업 수행
6. Team Admin Role의 관리자 권한에도 state와 Terraform 운영 경로를 지키는 명시적 거부 정책 적용

## AWS 자원 관리 경계

```mermaid
flowchart LR
    subgraph Bootstrap[bootstrap state가 관리]
        State[S3 원격 state<br/>버전 · 암호화 · 잠금]
        Roles[Plan · Apply · Bootstrap 역할]
        TeamAccess[팀 공통 관리자 역할 · 그룹]
    end

    subgraph Project[project state가 관리]
        Monitoring[모니터링<br/>EC2 · 보안 그룹 · IAM · S3]
        Airflow[Airflow<br/>EC2 · 보안 그룹 · IAM]
        GraphDB[GraphDB<br/>EC2 · 보안 그룹 · IAM]
    end

    subgraph Reference[조회하여 참조]
        Network[기본 VPC · 서브넷 · 라우팅]
        ManagedPolicy[AWS 관리형 IAM 정책]
    end

    subgraph External[다른 주체가 관리]
        Data[Glue · Athena · 파이프라인 데이터]
        Delivery[ECR · GitHub OIDC · CI 역할]
        ServiceIdentity[홈서버 서비스 IAM]
        Backup[AMI · EBS 스냅샷]
    end

    Network --> Monitoring
    Network --> Airflow
    Network --> GraphDB
    ManagedPolicy --> Roles
    ManagedPolicy --> Monitoring
    ManagedPolicy --> Airflow
    ManagedPolicy --> GraphDB

    classDef managed fill:#dcfce7,stroke:#15803d,color:#111827;
    classDef reference fill:#e8f1ff,stroke:#2563eb,color:#111827;
    classDef external fill:#f3f4f6,stroke:#4b5563,color:#111827;
    class State,Roles,TeamAccess,Monitoring,Airflow,GraphDB managed;
    class Network,ManagedPolicy reference;
    class Data,Delivery,ServiceIdentity,Backup external;
```

### 관리 원칙

- `bootstrap state`: Terraform 자체 운영 기반과 접근 권한 관리
- `project state`: 장기 운영하는 핵심 서버와 서버 전용 종속 자원 관리
- `조회하여 참조`: 계정 기본·공유 자원을 재생성하지 않고 기존 식별자 사용
- `다른 주체가 관리`: 파이프라인·배포·서비스 계정 등 실제 생성 주체의 책임 유지

## 현재 한계와 다음 확장

- 팀 테스트용 보안 그룹 연결은 Terraform 영구 구성에 넣지 않은 운영 예외이며 project plan에 차이가 표시될 수 있음
- GitHub Actions는 현재 정적 검증만 수행하며 실제 AWS plan 권한을 보유하지 않음
- 다음 확장은 GitHub OIDC 전용 읽기 역할을 추가해 PR plan과 정기 drift 탐지를 자동화하는 작업
