# Terraform 계획 역할 사용 절차

## 목적

- 지정 운영자의 평상시 AWS 권한과 Terraform 조회 권한 분리
- `terraform plan`에 필요한 project state 읽기와 AWS 설정 조회만 허용
- 계획 단계에서 state 본문 쓰기와 실제 인프라 변경 차단
- MFA가 확인된 1시간 역할 세션만 사용

## 역할 생성 전 준비

1. 공유하던 IAM 로그인 사용 중단
2. 지정 운영자의 개인 IAM 사용자와 MFA 장치 준비
3. 실제 사용자명과 프로젝트 S3 버킷 ARN을 Git 제외 tfvars에 기록
4. bootstrap 저장 plan이 IAM 자원 세 개만 생성하는지 검사
5. 기존 권한은 역할 검증이 끝날 때까지 유지

MFA를 등록하지 않으면 역할은 생성할 수 있어도 역할 전환은 거부됨.

## AWS CLI 프로파일

로컬 `~/.aws/config`에 실제 값을 넣어 역할 프로파일 구성. 이 파일과 실제 ARN은 저장소에 커밋하지 않음.

```ini
[profile terraform-plan]
role_arn = arn:aws:iam::<AWS_ACCOUNT_ID>:role/4EVR0TerraformPlanRole
source_profile = <OPERATOR_SOURCE_PROFILE>
mfa_serial = arn:aws:iam::<AWS_ACCOUNT_ID>:mfa/<OPERATOR_USER_NAME>
role_session_name = terraform-plan
region = ap-northeast-2
```

역할 전환 확인:

```bash
AWS_PROFILE=terraform-plan aws sts get-caller-identity
```

MFA 코드 입력 후 반환된 ARN에 `assumed-role/4EVR0TerraformPlanRole/`이 포함돼야 함.

## 계획 실행

```bash
AWS_PROFILE=terraform-plan \
  .local/bin/terraform -chdir=environments/project init \
  -backend-config=../../.local/project.tfbackend

AWS_PROFILE=terraform-plan \
  .local/bin/terraform -chdir=environments/project plan
```

역할 세션에는 다음 권한만 포함:

- project state 객체 읽기
- project lock 객체 생성·조회·삭제
- EC2 설정 조회
- 현재 관리 중인 IAM 설정 조회
- 지정 프로젝트 S3 버킷 설정 조회

## 차단 검증

역할 적용 후 성공 확인만으로 완료 처리하지 않음. 별도 역할 세션에서 다음 조건을 확인.

- `terraform plan` 성공
- project state 객체에 대한 `PutObject` 거부
- 프로젝트 S3 데이터 객체에 대한 `GetObject` 거부
- EC2 변경 명령 거부
- bootstrap state 접근 거부
- 세션 종료 후 임시 자격 증명 만료

차단 시험에는 운영 자원을 실제로 변경하지 않는 API 또는 별도 시험 객체 사용. 결과와 실행 시각은 `docs/private/`에 기록.

## 다음 단계

- 계획 역할 검증 완료
- 팀원의 임시 인프라 테스트 종료 후 project plan 드리프트 재검증
- 적용 역할을 별도 PR로 추가
- 적용 역할은 지정 운영자만 전환하고 project state 쓰기와 검토된 프로젝트 변경만 허용
- 계획·적용 역할 검증 후 기존 운영자의 불필요한 상시 관리자 권한 축소
- 일반 팀원은 Terraform 역할 대신 담당 서비스별 역할 사용
