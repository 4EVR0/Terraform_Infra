# 팀 공통 관리자 역할 사용 절차

## 목적

- 담당 영역이 유동적인 소규모 팀에 필요한 공통 AWS 관리자 권한 제공
- 팀원별 IAM 사용자와 MFA로 실제 작업자 구분
- 장기 액세스 키에 관리자 권한을 직접 연결하지 않고 최대 2시간 임시 역할 세션 사용
- Terraform 운영 자원과 state를 일반 관리자 작업에서 보호

## 구조

`4EVR0TeamUsers` 그룹은 다음 권한만 제공.

- 본인 비밀번호 변경
- 본인 가상 MFA 장치 생성·등록·교체
- `4EVR0TeamAdminRole` 전환

`4EVR0TeamAdminRole`은 명시된 팀원 IAM 사용자만 MFA를 사용해 전환 가능. 역할에는 AWS 관리형 `AdministratorAccess`가 연결되며 최대 세션은 2시간.

## 보호 조건

팀 관리자 역할에서도 다음 작업은 명시적으로 거부.

- bootstrap·project state 객체와 과거 버전 삭제
- state 버킷 삭제
- PlanRole·ApplyRole·BootstrapAdminRole·TeamAdminRole의 정책·신뢰 관계 변경과 삭제
- Terraform 운영자의 로그인·액세스 키·MFA·정책·그룹·사용자 정보 변경과 삭제

보호 대상 변경은 `TerraformBootstrapAdminRole`에서 검토한 Terraform plan으로만 수행.

## 최초 등록

1. 개인 IAM 사용자로 로그인
2. 최초 비밀번호 변경
3. 보안 자격 증명에서 본인 MFA 장치 등록
4. MFA를 사용해 팀 관리자 역할 전환
5. 반환된 역할 ARN과 세션 만료 시간 확인

MFA 등록 전에는 역할 신뢰 정책 때문에 관리자 역할 전환 불가.

## 콘솔 역할 전환

AWS 콘솔의 **Switch role**에서 다음 값을 사용.

- Account: 현재 프로젝트 AWS 계정
- Role: `4EVR0TeamAdminRole`
- Display name: 개인을 구분할 수 있는 이름

개인 IAM 사용자 로그인 시 MFA 인증을 완료한 상태여야 함.

## CLI 프로필

각 팀원의 로컬 `~/.aws/config`에 본인의 source profile과 MFA 장치를 사용해 설정.

```ini
[profile 4evr0-team-admin]
role_arn = arn:aws:iam::<AWS_ACCOUNT_ID>:role/4EVR0TeamAdminRole
source_profile = <PERSONAL_SOURCE_PROFILE>
mfa_serial = arn:aws:iam::<AWS_ACCOUNT_ID>:mfa/<PERSONAL_IAM_USER_NAME>
role_session_name = <PERSONAL_IAM_USER_NAME>
duration_seconds = 7200
region = ap-northeast-2
```

역할 전환 확인:

```bash
AWS_PROFILE=4evr0-team-admin aws sts get-caller-identity
```

반환된 ARN에 `assumed-role/4EVR0TeamAdminRole/`과 본인 사용자명이 포함돼야 함.

## 운영 규칙

- 액세스 키는 CLI 사용이 필요한 팀원에게만 발급
- 액세스 키 자체에는 서비스 관리자 정책을 연결하지 않음
- 관리자 작업은 반드시 MFA 역할 세션에서 수행
- 역할 세션 이름은 개인 IAM 사용자명으로 설정
- CLI 역할 세션은 최대 2시간으로 요청
- 작업 완료 후 세션 종료
- 팀 탈퇴 시 그룹 구성에서 사용자명을 제거하고 새 plan 검토 후 적용
- CloudTrail에서 AssumeRole 이벤트와 역할 세션 이름으로 작업자 추적

## 한계

- `AdministratorAccess`는 영향 범위가 크므로 실수와 세션 탈취 위험이 남음
- 인라인 거부 정책은 AWS Organizations SCP와 같은 조직 수준 통제가 아님
- 역할과 무관한 신규 IAM 사용자·역할을 생성해 우회할 수 있으므로 CloudTrail 점검 필요
- 팀 역할이 안정되면 실제 사용 기록을 바탕으로 서비스별 권한 분리 재검토
