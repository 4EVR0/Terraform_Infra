# Terraform 적용 역할 사용 절차

## 목적

- 코드 검토와 실제 AWS 변경 권한 분리
- 지정 운영자만 MFA 세션으로 검토된 저장 plan 적용
- project state 쓰기 권한을 적용 시점에만 사용
- 현재 Terraform 관리 대상 밖의 자원 변경 차단

## 권한 범위

적용 역할은 계획 역할의 조회 권한에 다음 권한을 추가.

- project state 객체 쓰기
- project lock 객체 생성·조회·삭제
- 등록된 EC2의 시작·중지와 인플레이스 설정 변경
- 등록된 보안 그룹의 규칙 변경
- 등록된 IAM 역할·인스턴스 프로파일·고객 관리형 정책 변경
- 검토된 관리형 정책과 등록된 IAM 역할 사이의 연결 변경
- 지정 S3 버킷의 암호화·공개 차단·소유권·태그 설정 변경

실제 자원 ARN은 Git 제외 tfvars에서 관리. 공개 코드에는 계정·인스턴스·버킷 식별자를 기록하지 않음.

## 명시적 차단

다음 작업은 정책에서 명시적으로 거부.

- EC2 인스턴스 생성과 종료
- 네트워크 인터페이스·보안 그룹·볼륨 생성과 삭제
- IAM 역할·인스턴스 프로파일·관리형 정책 생성과 삭제
- S3 버킷 생성과 삭제
- project state 삭제
- bootstrap state 읽기·쓰기·삭제

자원 교체가 필요한 변경은 일반 적용 절차로 처리하지 않음. 필요성, 백업, 중단 시간과 복구 절차를 별도로 검토한 뒤 권한 범위를 한시적으로 변경.

## 적용 전 게이트

1. 계획 역할로 최신 원격 state와 AWS 상태 조회
2. 의도하지 않은 드리프트가 없는지 확인
3. 저장 plan의 생성·변경·삭제 대상 검토
4. 원격 project state를 Git 제외 로컬 파일로 백업
5. PR의 검토 대상 커밋과 현재 `main` 일치 확인
6. 적용 역할의 MFA 세션 시작
7. 검토한 저장 plan 파일을 그대로 apply

드리프트가 있거나 `prevent_destroy`가 발생한 plan은 적용 금지. 현재 팀원의 임시 EC2 네트워크 테스트가 종료되기 전에는 project apply를 진행하지 않음.

## AWS CLI 프로파일

로컬 `~/.aws/config`에 실제 ARN과 MFA 장치를 넣어 별도 프로파일 구성.

```ini
[profile terraform-apply]
role_arn = arn:aws:iam::<AWS_ACCOUNT_ID>:role/4EVR0TerraformApplyRole
source_profile = <OPERATOR_SOURCE_PROFILE>
mfa_serial = arn:aws:iam::<AWS_ACCOUNT_ID>:mfa/<OPERATOR_USER_NAME>
role_session_name = terraform-apply
region = ap-northeast-2
```

역할 전환 확인:

```bash
AWS_PROFILE=terraform-apply aws sts get-caller-identity
```

반환된 ARN에 `assumed-role/4EVR0TerraformApplyRole/`이 포함돼야 함.

## 임시 자격 증명으로 적용

Terraform 프로세스에는 MFA로 발급한 역할 임시 자격 증명 사용. 장기 액세스 키나 역할 세션 값을 저장소에 기록하지 않음.

```bash
eval "$(aws configure export-credentials \
  --profile terraform-apply \
  --format env)"
```

이 명령은 AWS CLI가 발급한 임시 자격 증명을 현재 셸에만 설정. Terraform의 AWS SDK는 MFA 번호를 직접 요청하지 못하므로 `AWS_PROFILE=terraform-apply`만 지정하면 실행에 실패할 수 있음.

호출 주체를 다시 확인한 뒤 검토한 저장 plan만 적용.

```bash
aws sts get-caller-identity
```

```bash
.local/bin/terraform -chdir=environments/project apply \
  ../../.local/<REVIEWED_PLAN>.tfplan
```

적용 후 같은 역할 세션에서 새 plan을 생성해 의도한 변경 외 차이가 없는지 확인. 작업 기록에는 plan 요약, 적용 결과, 후속 plan 결과와 복구 지점을 남김.

작업을 마치면 현재 셸에서 임시 자격 증명을 제거.

```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_CREDENTIAL_EXPIRATION
```

## 한계

- 역할만으로 저장 plan 파일의 내용이나 특정 Git 커밋을 강제할 수 없음
- 적용 전 plan 검사와 PR 검토가 계속 필요
- 새 자원 생성, 기존 자원 삭제와 교체는 이 역할로 수행 불가
- 관리 대상 ARN이 바뀌면 bootstrap의 비공개 입력과 역할 정책을 먼저 갱신해야 함
