# Terraform 공용 상태 저장소 설계

## 목적과 현재 범위

- 기존 AWS 자원 import 전에 팀이 사용할 상태 저장·잠금·복구 기반 준비
- 사용자 결정: 팀 로그인 방식은 미정, 우선 기존 개인 AWS 로그인으로 준비
- 이번 구성은 전용 S3 버킷과 보호 설정만 생성 대상으로 정의
- IAM 사용자·역할 생성 및 정책 연결은 포함하지 않음
- 상태 저장소 생성 후 확인할 잠금·복원·원격 상태 이전은 별도 실환경 검증 단계

## 진행 상태

- 사용자 실행으로 버킷 생성 및 bootstrap 상태 이전 후 변경 없음 확인
- 사용자 콘솔 확인으로 bootstrap/project 두 상태 객체 존재 확인
- 활성 backend 선언은 코드에 반영. 실제 backend 값은 Git 제외 파일로 제공
- 아래 생성·이전 절차는 작업 이력 및 재구성 참고용. 현재 환경에 중복 실행하지 않음
- 사용자 실행으로 별도 verification 상태의 동시 실행 잠금·해제 확인
- 별도 텍스트 객체의 S3 버전 복구 PASS 기록 확인
- 격리된 verification key에서 Terraform state 과거 버전 복원, 변경 탐지, 최신 상태 재복원 후 `No changes` 확인
- 팀원별 접근 검증은 미완료

## 설계 선택

| 항목 | 선택 | 이유와 한계 |
|---|---|---|
| 저장소 | 기존 데이터 버킷과 분리한 전용 S3 버킷 | 상태와 파이프라인 데이터의 권한·삭제 주기 분리 |
| 구성 위치 | `bootstrap/state/` | 상태 저장소 관리와 프로젝트 자원 변경 분리 |
| 상태 경로 | bootstrap / project 두 경로 | 버킷 관리 상태와 프로젝트 상태의 덮어쓰기 방지 |
| 암호화 | SSE-S3(AES256) | 별도 KMS 키 운영 없이 암호화 적용. 키 권한 분리가 필요하면 추후 검토 |
| 과거 상태 | S3 버전 관리 | 이전 버전 복원 가능. 자동 만료 규칙은 초기 구성에 미포함 |
| 잠금 | S3 `use_lockfile=true` | 동시 변경 충돌 방지. 상태 백업과는 다른 역할 |
| 공개 접근 | 네 항목 차단, ACL 비활성 | 공개 정책·ACL을 통한 접근 방지 |
| 전송 | 일반 주체의 비 TLS 요청 거절 | 서비스 주체에 대한 네트워크 컨텍스트 예외 고려 |
| 삭제 | force_destroy=false, prevent_destroy=true | 실수로 버킷을 제거하는 변경 억제. 콘솔 삭제·구성 제거까지 보장하지 않음 |

S3 버킷은 하나지만 Terraform 상태 파일은 두 개. 상태 저장소 자체의 변경 주체와 일반 프로젝트 실행자의 권한을 분리할 수 있도록 설계.

## 생성할 구성

Terraform 관리 리소스 6개:

1. S3 버킷
2. 공개 접근 차단 설정
3. 객체 소유권 설정
4. 버전 관리 설정
5. 기본 암호화 설정
6. TLS 사용을 요구하는 버킷 정책

설정 리소스가 포함된 개수이므로 S3 버킷 6개를 만드는 것이 아님. 기존 EC2·데이터 버킷은 이 구성의 관리 대상에 포함되지 않음.

## 상태 파일과 접근 권한

- `4evr0/bootstrap/terraform.tfstate`: 상태 저장소 자체를 관리하는 상태
- `4evr0/project/terraform.tfstate`: 기존 프로젝트 AWS 자원을 편입할 상태
- 각 경로의 `.tflock`: 같은 상태에 대한 동시 작업을 제어하는 잠금 객체
- 초기에는 Terraform `default` workspace만 사용. 추가 workspace 사용 시 경로·권한 재설계 필요

권한 템플릿은 `backend_policies` 출력으로 제공하며, 실제 주체에 자동으로 연결하지 않음.

| 권한 | 범위 |
|---|---|
| ListBucket | 전용 버킷 내 키 이름 조회. Terraform workspace 탐색 고려 |
| GetObject / PutObject | 해당 범위의 상태 파일 하나 |
| GetObject / PutObject / DeleteObject | 해당 범위의 잠금 파일 하나 |

- 일반 backend 템플릿에는 상태 파일 삭제 권한 미포함
- 버킷 내용 조회 권한은 상태 파일 내용 읽기 권한과 구분
- backend 권한은 EC2·IAM 등 실제 인프라를 변경할 권한을 제공하지 않음
- 복구용 ListBucketVersions/GetObjectVersion 권한 및 버킷 관리 권한은 별도 관리 주체에 필요
- 기존 로그인에 더 넓은 정책이 연결돼 있다면, 좁은 템플릿을 추가하는 것만으로 기존 권한이 줄어들지 않음
- 팀 로그인 방식 확정 후 프로젝트용 backend 정책과 필요한 인프라 권한을 검토해 연결

## 준비와 계획 검토

아래 명령은 저장소 루트에서 실행. 다른 장비에서는 `.terraform-version`에 맞는 Terraform 설치 필요.

```bash
# 새 checkout에서 실제 값은 Git 제외 파일로 입력
cp bootstrap/state/terraform.tfvars.example bootstrap/state/local.auto.tfvars

.local/bin/terraform -chdir=bootstrap/state init -backend=false
.local/bin/terraform -chdir=bootstrap/state validate
.local/bin/terraform -chdir=bootstrap/state test
.local/bin/terraform -chdir=bootstrap/state plan -out=../../.local/state-bootstrap.tfplan
```

기존 `local.auto.tfvars.json`이 있으면 예시를 중복 복사하지 않고 해당 파일 수정.

계획 검토 기준:

- 대상 AWS 계정과 리전, 전용 버킷 이름 확인
- `6 to add, 0 to change, 0 to destroy` 확인
- 기존 버킷 재사용·IAM 권한 연결·서버 기동이 포함되지 않는지 확인
- plan은 AWS 쓰기 권한과 버킷 이름 사용 가능성을 보장하지 않음. 실제 생성 시 충돌·권한 오류가 날 수 있음
- 검토한 plan 적용은 별도 실행 단계. 계획 생성만으로 버킷이 만들어지지 않음

## 생성 후 원격 상태 이전 순서

1. 저장한 bootstrap plan을 적용한 뒤 버킷 보호 설정 실제 확인
2. 로컬 bootstrap state를 Git 제외 위치에 백업하고 권한 제한
3. bootstrap 출력의 backend_configs를 bootstrap/project용 로컬 `.tfbackend` 파일로 저장
4. `bootstrap/state/backend.tf.example`을 `backend.tf`로 활성화
5. bootstrap에서 `terraform init -migrate-state -backend-config=...` 실행
6. S3 bootstrap 상태 객체 확인 후 다시 plan하여 변경 없음 확인
7. project의 backend 예시를 활성화하고 project 경로로 초기화. 로컬 state가 존재하면 백업 후 migrate-state 사용
8. 서로 다른 backend key를 사용하는지 확인

새 버킷의 버전 관리가 활성화되고 정상 동작하는지 확인한 다음 상태를 저장. bootstrap state도 원격으로 옮긴 뒤 팀 공용 운영 시작.

버킷 자체를 관리하는 상태도 같은 버킷에 있으므로 버킷 손실은 양쪽 상태에 영향을 줌. 비공개 별도 보관 위치에 state 백업을 확보하고 버킷 손실 시 재구성 절차를 유지. Git의 `.tf` 코드만으로 state와 애플리케이션 데이터를 복구할 수는 없음.

## 실환경 검증 계획 — 생성 이후 실행

- 버전 관리: 테스트 상태에서 두 번 저장한 버전과 VersionId 확인
- 잠금: 프로젝트 상태와 분리된 임시 검증 key에서 두 Terraform 실행을 겹쳐 실행. 두 번째 실행의 잠금 획득 실패·대기 확인
- 잠금 해제: 첫 실행 종료 후 같은 key에 대한 다음 실행 성공 확인
- 복구: 임시 key의 이전 버전을 복사해 최신 버전으로 복원하고 내용 일치 확인
- 실제 bootstrap/project state는 검증용 데이터로 덮어쓰지 않음
- 실제 복구 시 모든 writer 중지·잠금 상태 확인 후 진행. 활동 중인 실행자의 잠금을 강제로 제거하지 않음

실제 Terraform 상태를 사용한 복구 시험의 구성, 단계별 의미, 결과와 한계는 [Terraform 상태 복구 검증](verify-state-recovery.md)에 기록.

모의 테스트는 구성의 보호 조건을 검증하며 실제 S3 잠금·IAM 접근·버전 복원 성공을 입증하지 않음.

## 공식 근거

- [Terraform S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3): S3 잠금, 버전 관리 권장, 상태·잠금 파일별 필요 권한
