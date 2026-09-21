# 4EVR0 Terraform 마이그레이션

[![Terraform checks](https://github.com/4EVR0/Terraform_Infra/actions/workflows/terraform-checks.yml/badge.svg)](https://github.com/4EVR0/Terraform_Infra/actions/workflows/terraform-checks.yml)

프로젝트에서 사용하는 AWS 인프라 전체를 코드로 관리하기 위한 작업 공간.
첫 목표는 **기존 자원의 재생성 없이 Terraform 관리 대상으로 편입**. 이후 변경 이력 관리와 장애 복구 검증으로 확장.

전체 변경 흐름과 state·IAM·AWS 자원의 관계는 [Terraform 운영 아키텍처](docs/architecture.md) 참조.

## 현재 상태 — 2026-09-20

- 서울 리전과 일부 글로벌 서비스의 AWS 실물 조회 완료
- 실제 자원 목록·상태·보안 설정은 로컬 인벤토리에서 관리
- Terraform 1.16.1 로컬 설치, AWS provider 6.63.0 선택 및 lock 파일 생성
- 활성 Terraform 구성: 기존 VPC·EC2 조회, 모니터링·Airflow·GraphDB EC2와 전용 보안 그룹·IAM 관리
- 이후 진행: 전용 상태 버킷 생성 및 bootstrap/project 원격 상태 저장 확인(사용자 실행·확인)
- 운영 검증: 사용자 실행으로 동시 실행 잠금·해제, 별도 S3 객체 버전 복구, 격리된 Terraform state 복원 후 plan 확인
- 완료된 편입: 사용자가 모니터링 EC2, 전용 보안 그룹·규칙, 연결 IAM 자원·S3 import 적용 후 각각 `No changes` 확인
- 완료된 EC2 편입: 모니터링, Airflow와 GraphDB. 사용자가 각각 적용 후 `No changes` 확인
- 완료된 Airflow 종속 자원 편입: 전용 보안 그룹 1개·규칙 4개와 IAM 자원 7개. 원격 state 등록 및 `No changes` 확인
- 완료된 GraphDB 종속 자원 편입: 전용 보안 그룹·규칙과 IAM 자원 10개. 원격 state 등록 및 `No changes` 확인
- 논문 크롤링 EC2: 비공개 복구용 AMI와 스냅샷 완료 확인 후 폐기. 재사용 시 재생성 가능한 배치 환경으로 설계 예정
- 파이프라인 백업 AMI·스냅샷은 Terraform 밖의 수동 운영 산출물로 분류
- 완료된 공용 자원 편입: 프로젝트 공용 SSH 보안 그룹과 규칙 2개. 원격 state 등록 및 `No changes` 확인
- 공용 SSH 정리 완료: 마지막 사용처 제거 후 그룹과 규칙 세 개 삭제, 후속 `No changes` 확인
- 지정 운영자용 Terraform 계획·적용 역할의 적용, MFA 전환과 권한 경계 검증 완료
- MFA 기반 비상 관리자 역할과 state·핵심 IAM 삭제 방지 조건 검증 완료
- 운영자 IAM 사용자의 상시 `AdministratorAccess` 제거 완료
- 세 팀원용 MFA 기반 공통 관리자 역할·그룹 적용 완료. 역할 신뢰 대상, 2시간 세션, 보호 정책과 그룹 멤버십 확인 후 bootstrap plan `No changes` 확인
- 팀원별 최초 비밀번호 변경·MFA 등록·역할 전환은 사용 절차와 함께 각 팀원에게 인계
- 기본 네트워크는 조회 대상으로, Glue·배포·서비스 계정·백업 산출물은 외부 관리 대상으로 분류
- 팀원의 임시 EC2 네트워크 테스트 변경은 Terraform 영구 구성에 넣지 않는 운영 예외로 수용
- Terraform 마이그레이션 상태: **완료**. 핵심 서버·종속 자원·상태 저장소·접근 경로 편입과 나머지 자원의 관리 경계 확정

검증 결과:

- `terraform fmt -check -recursive`: 통과
- `terraform validate`: 통과
- 실제 AWS 대상 조회용 `terraform plan`: 통과. 기존 VPC·EC2 조회, 출력값 추가만 제안
- 인벤토리 스크립트: AWS 조회 실행 완료, Python 문법 검사 통과
- 모니터링 EC2 import 적용 및 이후 변경 없음 확인 완료(사용자 실행 결과)
- 모니터링 보안 그룹·규칙 9개 import 적용 완료. 원격 state 등록 확인 및 후속 `No changes` 확인
- 모니터링 IAM 5개 import 적용 완료. 원격 state 등록 확인 및 후속 `No changes` 확인
- 모니터링 S3 4개 import 적용 완료. 원격 state 등록 확인 및 후속 `No changes` 확인
- Airflow EC2 import 적용 완료. 원격 state 등록 확인 및 후속 `No changes` 확인
- Airflow 전용 보안 그룹 1개와 규칙 4개 import 적용 완료. 원격 state 등록 확인 및 후속 `No changes` 확인
- Airflow IAM 역할·인스턴스 프로파일·관리형 정책 연결 7개 import 적용 완료. 원격 state 등록 확인 및 후속 `No changes` 확인
- GraphDB EC2 보안 조치 후 새 계획에서 `1 to import, 0 to add, 0 to change, 0 to destroy`와 빈 user data 확인
- GraphDB EC2: 자격 정보 교체와 user data 제거 후 새 계획에서 import 1건 외 변경 없음 및 보안 검사 통과
- GraphDB EC2와 연결 자원 적용 완료. 원격 state 등록 및 후속 `No changes` 확인
- 공용 SSH 보안 그룹 계획: `3 to import, 0 to add, 0 to change, 0 to destroy`
- 공용 SSH 보안 그룹 적용 완료. 원격 state 등록 및 후속 `No changes` 확인

## 범위

| 구분 | 이번 마이그레이션의 처리 방향 |
|---|---|
| 프로젝트 전용 EC2·EBS·EIP·보안 그룹 | 기존 ID 유지, 현재 속성을 코드에 반영한 뒤 import |
| 프로젝트 전용 S3·IAM | 실제 사용 관계를 확인한 자원과 연결 설정만 단계별 편입 |
| ECR·CI IAM·파이프라인 데이터 S3 | 기존 빌드·배포·데이터 운영 주체가 관리 |
| 기본 VPC·서브넷·라우팅·인터넷 게이트웨이 | 계정 기본 네트워크로 분류하고 조회 대상으로 참조 |
| AWS 관리형 IAM 정책 | 정책 자체를 생성하지 않고 필요한 연결 관계 관리 |
| Glue/Iceberg 테이블 | 파이프라인이 생성·변경하므로 Terraform 관리에서 제외 |
| Vast.ai GPU·Tailscale·홈서버·개발 PC | AWS 마이그레이션 밖의 의존성으로 기록 |
| Docker Compose·애플리케이션 배포 | 기존 저장소에서 관리. Terraform은 AWS 자원과 접근 권한에 집중 |

여기서 “AWS 전체”는 **프로젝트가 소유·사용하는 AWS 자원 전체**를 의미. 계정에서 발견된 모든 자원을 일괄 편입한다는 의미는 아님.

## 파일 구성

```text
Terraform_Infra/
├── README.md
├── docs/
│   └── migration-plan.md        # 공개 가능한 작업 순서·완료 기준
├── scripts/inventory.py         # AWS 읽기 전용 조회
├── environments/project/
│   ├── versions.tf             # 도구·provider 제약
│   ├── providers.tf            # 계정 제한·서울 리전
│   ├── discovery.tf            # 기존 자원 조회
│   ├── variables.tf            # 실제 계정·자원 ID를 외부 입력으로 분리
│   ├── terraform.tfvars.example # 실제 값 없는 설정 예시
│   ├── .terraform.lock.hcl     # 실제 provider 버전·체크섬
│   ├── imports.tf             # 모니터링 EC2 import 선언
│   ├── monitoring.tf          # 검토한 EC2 속성 관리
│   ├── monitoring-variables.tf # 비공개 설정의 입력 타입
│   ├── monitoring-security-group.tf # 전용 보안 그룹과 규칙 관리
│   ├── monitoring-security-group-variables.tf # 비공개 규칙 입력 타입
│   ├── monitoring-iam.tf     # 연결 IAM 자원과 import 선언
│   ├── monitoring-iam-variables.tf # 비공개 정책 입력 타입
│   ├── monitoring-s3.tf      # 모니터링 버킷과 보호 설정 관리
│   ├── monitoring-s3-variables.tf # 비공개 버킷 입력 타입
│   ├── airflow.tf           # Airflow EC2 import와 검토한 속성 관리
│   ├── airflow-variables.tf # Airflow 비공개 설정의 입력 타입
│   ├── airflow-security-group.tf # Airflow 전용 보안 그룹과 규칙 관리
│   ├── airflow-security-group-variables.tf # 비공개 규칙 입력 타입
│   ├── airflow-iam.tf      # Airflow IAM 역할·프로파일·정책 연결 관리
│   ├── airflow-iam-variables.tf # 비공개 IAM 설정의 입력 타입
│   ├── graphdb.tf          # GraphDB EC2 import와 검토한 속성 관리
│   ├── graphdb-variables.tf # GraphDB 비공개 설정의 입력 타입
│   ├── backend.tf.example     # 원격 상태 저장 설정, 현재 비활성
│   └── backend.tfbackend.example
├── inventory/raw/              # 로컬 전용 원본 응답, Git 제외
└── .local/                     # 로컬 실행 파일·plan, Git 제외
```

프로젝트 규모를 고려해 우선 하나의 구성 디렉터리 사용. 관리 주체나 변경 주기가 실제로 달라질 때 상태 파일 분리·모듈화 검토.

## 로컬 실행

저장소 최상위 `Terraform_Infra`에서 실행. AWS CLI 인증은 기존 프로파일 또는 환경 변수 사용. 키를 `.tf` 파일에 기록하지 않음.

```bash
# 이번 장비에 준비한 Terraform 사용. 다른 장비는 .terraform-version 버전 설치 필요.
.local/bin/terraform version

# 새 checkout에서만 예시를 복사한 뒤 실제 값 입력.
# local.auto.tfvars.json이 이미 있으면 복사하지 않고 해당 파일 사용.
cp environments/project/terraform.tfvars.example environments/project/local.auto.tfvars

# 실제 계정 ID를 환경 변수에 설정한 뒤 읽기 전용 조회 실행.
python3 scripts/inventory.py --profile default --regions ap-northeast-2 --expected-account-id "$AWS_EXPECTED_ACCOUNT_ID"

# 활성화된 전체 리전의 지원 서비스 조회. --regions와 동시 사용 불가.
python3 scripts/inventory.py --profile default --all-regions --expected-account-id "$AWS_EXPECTED_ACCOUNT_ID"

.local/bin/terraform -chdir=environments/project init -backend-config=../../.local/project.tfbackend
.local/bin/terraform fmt -check -recursive
.local/bin/terraform -chdir=environments/project validate
.local/bin/terraform -chdir=environments/project plan
```

- 현재 원격 state에는 모니터링 EC2와 종속 보안 그룹·IAM·S3, Airflow EC2와 전용 보안 그룹·IAM이 등록되어 있으며 후속 plan은 `No changes`
- 새 checkout은 실제 버킷·key·계정 제한이 담긴 로컬 `.tfbackend` 파일을 비공개로 준비한 뒤 초기화
- `.example` 파일은 Terraform이 읽지 않는 검토용 파일
- provider의 `allowed_account_ids`로 다른 계정에 대한 실행 방지
- 원본 응답·상태·plan은 공개 문서에 붙이지 않고 로컬 보관
- 실제 AWS 계정·자원 ID는 Git에서 제외된 `local.auto.tfvars` 또는 `local.auto.tfvars.json`에 입력
- 상세 인벤토리 `docs/inventory*.md`는 로컬에만 보관. 공개 문서에는 실제 ID·접속 주소·보안 설정을 기록하지 않음
- 상세 작업 일지·조사 근거·자원별 소유 범위는 `docs/private/`에 기록하고 Git에서 제외
- `sensitive` 출력은 화면 표시를 줄이는 기능이며, state·plan에 값이 저장되는 것을 막지 않음
- 인벤토리의 `ABSENT`: 해당 설정이 없다는 API 응답. `UNRESOLVED`: 권한·통신 등으로 확인하지 못한 항목
- 서비스 목록 조회는 선택한 API 범위만 포함. 빈 결과와 미조회 항목 구분 필수

인벤토리 회귀 검사: `python3 -m unittest discover -s tests -v`. 계정 불일치 중단, 활성 리전 선택, 권한 오류와 설정 부재의 구분 검증. 테스트는 실제 AWS에 접근하지 않음.

## 다음 작업

Terraform 마이그레이션의 필수 작업은 완료. 이후 작업은 새로운 자원을 추가할 때 [AWS 인벤토리 관리 경계](docs/aws-management-boundary.md)를 갱신하고, 필요에 따라 정기 drift 탐지와 서비스 복구 시험을 별도 운영 개선으로 진행.

PR에서 자동 실행되는 형식·구성·회귀 검사의 범위와 로컬 재현 방법은 [Terraform PR 자동 검증](docs/ci-validation.md) 참조.

마이그레이션 이후 CI 검증·읽기 전용 plan·drift 탐지와 포트폴리오 문서화의 우선순위는 [Terraform 포트폴리오 고도화 로드맵](docs/terraform-portfolio-roadmap.md) 참조.

세부 작업과 판단 기준은 [마이그레이션 계획](docs/migration-plan.md) 참조. 상세 인벤토리는 별도 로컬 문서에서 확인.

팀원의 plan 권한과 관리자 apply 권한 분리안은 [팀 Terraform 접근 권한 설계](docs/team-terraform-access.md) 참조.

지정 운영자용 계획 역할의 준비·사용·차단 검증 순서는 [Terraform 계획 역할 사용 절차](docs/use-terraform-plan-role.md) 참조.

지정 운영자용 적용 역할의 권한 범위와 적용 게이트는 [Terraform 적용 역할 사용 절차](docs/use-terraform-apply-role.md) 참조.

비상 관리자 역할의 사용 조건과 상시 관리자 권한 제거 게이트는 [Terraform 비상 관리자 역할 사용 절차](docs/use-terraform-bootstrap-admin-role.md) 참조.

팀 공통 관리자 역할의 MFA 등록과 콘솔·CLI 사용 절차는 [팀 공통 관리자 역할 사용 절차](docs/use-team-admin-role.md) 참조.

작업 이력은 [작업 기록](docs/worklog.md), 인벤토리 도구의 범위와 한계는 [조사 절차](docs/discovery-workflow.md) 참조.

공용 상태 저장소 구성은 `bootstrap/state/`, 설계와 적용 순서는 [상태 저장소 설계](docs/state-backend.md) 참조. 사용자 실행으로 버킷 생성 및 두 상태 객체 저장 확인. 동시 실행 잠금, 별도 S3 객체 버전 복구와 격리된 Terraform state 복원 후 plan 검증 완료. 상세 시험은 [Terraform 상태 복구 검증](docs/verify-state-recovery.md) 참조.

첫 편입의 범위와 사용자 적용 절차는 [모니터링 EC2 import](docs/import-monitoring.md) 참조. 앞으로 작업 브랜치 → PR → 리뷰·머지 → 새 plan 검토 → 사용자 apply 순서로 진행.

모니터링 보안 그룹의 편입 범위, 적용 결과와 한계는 [모니터링 보안 그룹 import](docs/import-monitoring-security-group.md) 참조.

모니터링 IAM의 관리 경계, 정책 보관 방식과 적용 절차는 [모니터링 IAM import](docs/import-monitoring-iam.md) 참조.

모니터링 S3의 편입 범위, 데이터 보호 선택과 적용 절차는 [모니터링 S3 import](docs/import-monitoring-s3.md) 참조.

Airflow EC2의 대상 선정, 관리 범위와 적용 절차는 [Airflow EC2 import](docs/import-airflow-ec2.md) 참조.

Airflow 전용 보안 그룹의 소유 경계, 규칙 관리 방식과 적용 절차는 [Airflow 보안 그룹 import](docs/import-airflow-security-group.md) 참조.

Airflow IAM의 소유 경계, 정책 연결 관리 방식과 적용 절차는 [Airflow IAM import](docs/import-airflow-iam.md) 참조.

논문 크롤링 EC2의 편입 보류 근거와 재사용 시 권장 구조는 [논문 크롤링 EC2 관리 판단](docs/assess-pipeline-ec2.md) 참조.

논문 크롤링 EC2의 백업·폐기와 공용 SSH 자원 정리 계획은 [논문 크롤링 EC2 안전 폐기](docs/retire-pipeline-ec2.md) 참조.

GraphDB EC2의 편입 준비, 발견된 user data 위험과 적용 선행 조건은 [GraphDB EC2 편입](docs/import-graphdb-ec2.md) 참조.

공용 SSH 그룹의 단계적 제거 근거와 적용 게이트는 [GraphDB 공개 SSH 경로 단계적 제거](docs/harden-graphdb-ssh.md) 참조.

Airflow의 SSM 대체 경로 검증과 적용 게이트는 [Airflow 공개 SSH 경로 단계적 제거](docs/harden-airflow-ssh.md) 참조.

모니터링의 SSM 권한 추가 근거와 검증 순서는 [모니터링 서버 SSM 관리 경로 추가](docs/enable-monitoring-ssm.md) 참조.

모니터링의 공용 SSH 그룹 분리 근거와 적용 게이트는 [모니터링 공개 SSH 경로 단계적 제거](docs/harden-monitoring-ssh.md) 참조.
