# 4EVR0 Terraform 마이그레이션

프로젝트에서 사용하는 AWS 인프라 전체를 코드로 관리하기 위한 작업 공간.
첫 목표는 **기존 자원의 재생성 없이 Terraform 관리 대상으로 편입**. 이후 변경 이력 관리와 장애 복구 검증으로 확장.

## 현재 상태 — 2026-09-09 킥오프

- 서울 리전과 일부 글로벌 서비스의 AWS 실물 조회 완료
- 실제 자원 목록·상태·보안 설정은 로컬 인벤토리에서 관리
- Terraform 1.16.1 로컬 설치, AWS provider 6.63.0 선택 및 lock 파일 생성
- 활성 Terraform 구성: 기존 VPC·EC2를 읽는 `data` 블록만 포함
- 이후 진행: 전용 상태 버킷 생성 및 bootstrap/project 원격 상태 저장 확인(사용자 실행·확인)
- 운영 검증: 사용자 실행으로 동시 실행 잠금·해제 및 별도 S3 객체 버전 복구 확인
- 아직 수행하지 않은 작업: 기존 자원 import, Terraform state 자체의 복구 후 plan 검증
- 전체 AWS 인벤토리 완료 여부: **미완료**. 다른 리전·추가 서비스·권한 정책 세부 조사 필요

검증 결과:

- `terraform fmt -check -recursive`: 통과
- `terraform validate`: 통과
- 실제 AWS 대상 조회용 `terraform plan`: 통과. 기존 VPC·EC2 조회, 출력값 추가만 제안
- 인벤토리 스크립트: AWS 조회 실행 완료, Python 문법 검사 통과
- 자원 편입용 plan은 아직 생성하지 않음. 조회용 plan은 로컬 `.local/discovery.tfplan`에 보관

## 범위

| 구분 | 이번 마이그레이션의 처리 방향 |
|---|---|
| 프로젝트 전용 EC2·EBS·EIP·보안 그룹 | 기존 ID 유지, 현재 속성을 코드에 반영한 뒤 import |
| S3·ECR·IAM·Glue 등 프로젝트 AWS 자원 | 실제 사용 관계와 소유 범위 확인 후 단계별 편입 |
| 기본 VPC·서브넷·라우팅·인터넷 게이트웨이 | 공유 여부 확인 전까지 조회 대상으로 참조 |
| AWS 관리형 IAM 정책 | 정책 자체를 생성하지 않고 필요한 연결 관계 관리 |
| Glue/Iceberg 테이블 | 파이프라인이 생성·변경하는 테이블과 Terraform 소유 자원 구분 필요 |
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
│   ├── imports.tf.example     # 첫 import 후보, 현재 비활성
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

- 현재 `plan`은 VPC·EC2 조회와 출력값 계산만 수행
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

1. 인벤토리 누락 범위 조사 및 공유 자원 경계 확정
2. 전용 S3 상태 저장소와 팀 접근 권한 구성
3. 모니터링 EC2 한 대의 import 계획 생성·검토
4. `1 to import, 0 to add, 0 to change, 0 to destroy` 확인 후 편입
5. 나머지 자원 확대 및 복구 검증

세부 작업과 판단 기준은 [마이그레이션 계획](docs/migration-plan.md) 참조. 상세 인벤토리는 별도 로컬 문서에서 확인.

작업 이력은 [작업 기록](docs/worklog.md), 인벤토리 도구의 범위와 한계는 [조사 절차](docs/discovery-workflow.md) 참조.

공용 상태 저장소 구성은 `bootstrap/state/`, 설계와 적용 순서는 [상태 저장소 설계](docs/state-backend.md) 참조. 사용자 실행으로 버킷 생성 및 두 상태 객체 저장 확인. 동시 실행 잠금 및 별도 S3 객체 버전 복구 확인. Terraform state 자체의 복원 후 plan 검증은 미수행.
