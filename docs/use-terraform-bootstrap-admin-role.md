# Terraform 비상 관리자 역할 사용 절차

## 목적

- 운영자 IAM 사용자의 상시 `AdministratorAccess` 대체
- bootstrap state 복구와 IAM·backend 장애 대응을 MFA 임시 세션으로 제한
- 일상적인 plan·apply 작업과 계정 관리자 작업 분리
- 관리자 작업의 시작과 종료를 역할 세션으로 구분

## 권한 범위

`4EVR0TerraformBootstrapAdminRole`은 AWS 관리형 `AdministratorAccess`를 사용. 새 AWS 자원 생성, IAM 변경, bootstrap 구성 복구처럼 PlanRole과 ApplyRole의 범위를 벗어난 작업에만 사용.

다음 삭제 작업은 인라인 명시적 거부 정책으로 차단.

- bootstrap과 project state 객체 및 과거 버전 삭제
- Terraform state 버킷 삭제
- PlanRole, ApplyRole, BootstrapAdminRole 삭제
- 지정 운영자 IAM 사용자 삭제

state lock 객체 삭제는 장애 복구에 필요하므로 차단 대상에서 제외. 삭제 보호는 실수 방지 장치이며 관리자 역할이 자신의 정책을 변경할 수 있다는 한계가 있으므로 PR 검토와 작업 기록을 함께 사용.

## 사용 조건

- 지정 운영자 한 명만 역할 전환 가능
- MFA 인증 필수
- 역할 세션 최대 1시간
- 일상적인 조회는 PlanRole, 검토한 기존 자원 변경은 ApplyRole 사용
- 관리자 역할은 새 자원·IAM·backend 변경 또는 복구 작업에만 사용

## 로컬 프로필

```ini
[profile terraform-bootstrap-admin]
role_arn = arn:aws:iam::<AWS_ACCOUNT_ID>:role/4EVR0TerraformBootstrapAdminRole
source_profile = <OPERATOR_SOURCE_PROFILE>
mfa_serial = <OPERATOR_MFA_SERIAL>
role_session_name = terraform-bootstrap-admin
region = ap-northeast-2
```

역할 전환 확인:

```bash
AWS_PROFILE=terraform-bootstrap-admin aws sts get-caller-identity
```

반환된 ARN에 `assumed-role/4EVR0TerraformBootstrapAdminRole/`이 포함돼야 함.

## Terraform 실행

AWS CLI가 발급한 임시 역할 자격 증명을 현재 셸에만 설정.

```bash
eval "$(aws configure export-credentials \
  --profile terraform-bootstrap-admin \
  --format env)"
```

호출 주체를 확인하고 bootstrap state를 Git 제외 경로에 백업한 뒤, 검토한 저장 plan만 적용.

```bash
aws sts get-caller-identity

.local/bin/terraform -chdir=bootstrap/state state pull \
  > .local/bootstrap-state-before-admin-change.json

.local/bin/terraform -chdir=bootstrap/state apply \
  ../../.local/<REVIEWED_PLAN>.tfplan
```

작업 후 새 plan에서 `No changes`를 확인하고 임시 자격 증명을 제거.

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_CREDENTIAL_EXPIRATION
```

## 상시 관리자 권한 제거 게이트

운영자 IAM 사용자를 기존 관리자 그룹에서 제거하기 전에 다음 항목을 모두 확인.

1. MFA 기반 비상 관리자 역할 전환 성공
2. bootstrap state 읽기·쓰기와 과거 버전 조회 성공
3. state 객체·버킷 삭제 차단 확인
4. IAM 조회와 검토된 시험 작업 성공
5. 역할 세션 종료 후 운영자 직접 관리자 작업 차단 확인
6. root 계정 MFA와 비상 접근 절차 별도 확인

## 한계

- 강한 권한을 가진 역할이므로 역할 세션 탈취 시 세션 만료 전까지 영향 범위가 큼
- 인라인 거부 정책은 조직 SCP처럼 변경 불가능한 통제 수단이 아님
- 새 자원 생성과 복구 작업에도 저장 plan, 백업, PR 검토와 작업 기록 필요
- 팀과 AWS 계정 수가 늘어나면 IAM Identity Center와 Organizations SCP 도입 검토 필요
