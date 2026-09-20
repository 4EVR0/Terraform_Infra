# 팀 Terraform 접근 권한 설계

## 목표

- 팀원이 개인 AWS 자격 증명을 공유하지 않고 Terraform 계획을 검토할 수 있는 구조
- 코드 검토와 실제 인프라 적용 권한 분리
- 원격 state의 민감성과 잠금·복구 권한을 고려한 최소 권한 부여
- 사용자별 로그인과 역할 세션을 CloudTrail에서 구분 가능한 운영 방식

## 현재 조건

- 초기 운영 규모는 단일 AWS 계정과 소규모 팀을 기준으로 설정
- 기존 공유 로그인은 지정 운영자 개인 계정으로 전환하고 상시 관리자 권한 제거 완료
- 나머지 팀원의 개인별 IAM 사용자와 MFA 발급은 후속 작업으로 진행
- Terraform 역할 전환 권한은 지정 운영자 한 명에게만 부여
- 실제 로그인 주체와 MFA 등록 현황은 비공개 운영 기록에서 관리
- 전용 S3 backend에 bootstrap과 project state를 분리해 저장
- 실제 적용은 저장된 plan을 관리자가 실행하는 방식으로 운영

초기 단계에서는 개별 IAM 사용자, MFA, 역할 전환을 사용하고 계정이 늘어나거나 중앙 사용자 관리가 필요해질 때 Identity Center 도입 검토.

## 권한 구조

### 1. 팀원 기본 로그인

- 팀원마다 별도 IAM 사용자 사용
- 콘솔 또는 CLI 자격 증명 공유 금지
- 모든 사람의 MFA 등록 필수
- 사용자에는 프로젝트 자원 직접 변경 권한을 부여하지 않음
- 담당 서비스에 필요한 역할만 전환하도록 허용
- 사용자별 액세스 키는 CLI 사용이 필요한 경우에만 발급하고 정기 교체·폐기

### 2. Terraform 계획 역할

지정 운영자가 PR을 검토하고 `terraform plan`을 실행할 때 사용하는 짧은 세션 역할. 초기에는 한 명만 이 역할로 전환 가능.

- project state 읽기
- project lock 파일 생성·조회·삭제
- 프로젝트가 사용하는 AWS 서비스의 조회 권한
- state 본문 삭제, bootstrap state 접근, 인프라 변경 권한 제외
- 역할 세션 시간 제한과 MFA 조건 적용

계획 과정에서도 state 전체를 읽을 수 있으므로 일반 팀원에게 부여하지 않음. Terraform의 `sensitive` 표시는 화면 출력을 줄일 뿐 state 내용을 암호화하거나 숨기지 않음.

### 3. Terraform 적용 역할

검토된 저장 plan을 실제 적용하는 관리자용 역할.

- project state 읽기·쓰기와 lock 관리
- Terraform이 관리하는 프로젝트 자원 변경 권한
- state 버킷 삭제와 bootstrap state 변경 권한 제외
- MFA와 짧은 역할 세션 적용
- 팀 전체가 아닌 지정된 관리자만 역할 전환 가능

초기에는 지정 운영자 한 명에게만 적용 역할을 허용. 팀원이 코드 검토에 참여해도 AWS 조회와 변경은 PR 검토 후 운영자가 실행.

### 4. Terraform 비상 관리자

bootstrap state, IAM과 상태 버킷 자체를 복구하는 별도 비상 권한.

- 일반 plan·apply 역할에서 분리
- MFA가 확인된 1시간 역할 세션에만 관리자 권한 부여
- 버전 복원, backend 장애 대응과 새 인프라 구성 시에만 사용
- 일상적인 프로젝트 변경에는 사용하지 않음
- state 객체·버킷과 Terraform 역할·운영자 삭제를 명시적으로 거부
- 상태 복구 절차와 함께 접근 이력을 기록

### 5. 팀 공통 관리자

담당 영역이 유동적인 팀원들이 사용하는 MFA 기반 관리자 역할. 반복적인 역할 전환 부담과 관리자 권한 노출 시간을 함께 고려해 최대 2시간 세션 사용.

- 개인별 IAM 사용자와 MFA 사용
- IAM 사용자에는 본인 자격 증명 관리와 역할 전환 권한만 부여
- 역할 세션에만 `AdministratorAccess` 연결
- Terraform state·운영 역할·운영자 계정 변경은 명시적으로 차단
- CloudTrail에서 개인별 역할 세션 이름으로 작업자 구분

## 권한 비교

| 작업 | 계획 역할 | 적용 역할 | 비상 관리자 |
|---|---:|---:|---:|
| project state 읽기 | 허용 | 허용 | 필요 시 허용 |
| project lock 관리 | 허용 | 허용 | 필요 시 허용 |
| project state 쓰기 | 제외 | 허용 | 필요 시 허용 |
| AWS 자원 조회 | 허용 | 허용 | 허용 |
| 프로젝트 자원 변경 | 제외 | 허용 | 비상 작업 시 허용 |
| bootstrap state 변경 | 제외 | 제외 | 허용 |
| state 과거 버전 복원 | 제외 | 제외 | 허용 |

## 실행 흐름

1. 지정 운영자가 개인 IAM 사용자로 로그인하고 MFA 인증
2. 계획 역할로 전환
3. 저장소와 비공개 backend·변수 파일 준비
4. `terraform init`, `validate`, `plan` 실행
5. plan 요약과 자동 검사 결과를 PR에 첨부
6. 관리자 검토 후 적용 역할로 전환
7. 새 state 백업과 최신 plan 재생성
8. 저장 plan 적용 후 실제 AWS와 `No changes` 확인

## Terraform으로 관리할 범위

- 역할, 신뢰 정책, 역할 권한 정책, 역할 전환을 허용하는 그룹 정책
- backend project 경로와 lock 경로의 세부 권한
- 사용자 이름 목록은 Git 제외 입력으로 분리
- 로그인 비밀번호, MFA 장치, 액세스 키 비밀값은 Terraform state에 저장하지 않음

IAM 사용자 자체를 Terraform으로 만들 수 있지만 초기 비밀번호와 액세스 키를 코드로 관리하면 state에 민감 정보가 남을 수 있음. 이번 단계에서는 기존 개별 사용자 확인과 MFA 등록을 선행하고 역할·정책 연결만 코드화.

## 단계별 도입

1. 공유 로그인 중단과 개인별 IAM 사용자·MFA 준비
2. 지정 운영자만 전환 가능한 계획 역할 생성
3. 별도 자격 증명으로 `terraform plan` 성공과 state 쓰기·인프라 변경 차단 확인
4. 검토된 plan을 실행하는 적용 역할을 별도 변경으로 추가
5. MFA 기반 비상 관리자 역할과 삭제 방지 조건 검증
6. 기존 운영자의 상시 관리자 권한 제거

첫 구현은 계획 역할까지만 포함. 기존 사용자 권한 축소는 역할 검증 후 별도 변경으로 진행.

계획 역할의 권한 범위와 로컬 프로파일 설정, 적용 후 차단 시험은 [Terraform 계획 역할 사용 절차](use-terraform-plan-role.md) 참조.

## 계획 역할 검증 결과

- 지정 운영자 MFA 등록과 역할 전환 성공
- project state 읽기와 project lock 관리 허용 확인
- 현재 Terraform 관리 자원의 설정 조회 성공
- project state 쓰기와 bootstrap state 접근 거부 확인
- 프로젝트 S3 데이터 객체 읽기와 EC2 변경 요청 거부 확인
- 실제 적용 권한은 포함하지 않은 상태 유지

프로젝트 plan에서 별도로 발견한 팀원의 임시 네트워크 변경은 역할 권한 문제와 분리. 테스트 종료 후 코드 기준 상태로 복구하고 plan을 다시 확인.

## 적용 역할 구현 범위

- 지정 운영자 한 명만 MFA로 역할 전환
- project state 쓰기와 lock 관리 허용
- Git 제외 입력에 등록된 기존 자원의 인플레이스 변경만 허용
- EC2와 종속 네트워크 자원 생성·삭제, IAM 주요 자원 생성·삭제, S3 버킷 생성·삭제 명시적 거부
- bootstrap state 접근과 project state 삭제 명시적 거부
- 자원 교체가 필요한 변경은 별도 검토와 한시적 권한 변경 대상으로 분리

상세 적용 게이트와 로컬 프로파일 구성은 [Terraform 적용 역할 사용 절차](use-terraform-apply-role.md) 참조.

## 비상 관리자 역할 구현 범위

- 지정 운영자 한 명만 MFA로 역할 전환
- 최대 역할 세션 1시간
- AWS 관리형 `AdministratorAccess`로 bootstrap·IAM·신규 자원 복구 가능
- bootstrap과 project state 객체 및 과거 버전 삭제 명시적 거부
- state 버킷, 세 Terraform 역할과 지정 운영자 삭제 명시적 거부
- 평상시에는 PlanRole과 ApplyRole을 사용하고 비상 관리자 역할 사용 이력 별도 기록

상세 사용 조건과 상시 관리자 권한 제거 게이트는 [Terraform 비상 관리자 역할 사용 절차](use-terraform-bootstrap-admin-role.md) 참조.

## 비상 관리자 역할 검증 결과

- 지정 운영자의 MFA 역할 전환과 1시간 세션 확인
- bootstrap state 버전·Terraform state·IAM 조회 성공
- state와 분리된 검증 객체의 생성, 암호화와 전체 버전 정리 성공
- state 객체·과거 버전·버킷과 핵심 IAM 삭제 차단 확인
- 루트 계정 MFA 활성화와 루트 액세스 키 부재 확인
- 운영자의 상시 관리자 그룹 권한 제거
- 운영자 직접 자격 증명에서 IAM 역할 생성, EC2 종료와 S3 버킷 삭제 거부 확인
- 비상 관리자 역할 세션의 후속 bootstrap plan에서 `No changes` 확인

## 팀 공통 관리자 역할 구현 범위

- Git 제외 입력에 등록된 팀원 IAM 사용자만 신뢰
- MFA 필수와 최대 세션 2시간 적용
- 사용자 공통 그룹에서 본인 비밀번호·MFA 관리와 TeamAdminRole 전환만 허용
- 역할 세션에 AWS 관리형 `AdministratorAccess` 연결
- state와 Terraform 운영 자원은 인라인 거부 정책으로 보호
- Terraform 전용 세 역할과 운영 계정은 기존 지정 운영자만 관리

팀원 등록과 콘솔·CLI 사용 절차는 [팀 공통 관리자 역할 사용 절차](use-team-admin-role.md) 참조.

## 적용 전 확인 항목

- 개인별 IAM 사용자와 담당 역할 명단
- 모든 참여자의 MFA 등록
- 팀원이 plan을 위해 읽어야 하는 AWS 서비스 목록
- 적용 역할이 변경할 Terraform 관리 자원 목록
- project state 읽기 권한이 팀 내에서 허용되는지
- 비공개 tfvars 전달과 보관 방식
- 역할 회수와 프로젝트 종료 시 자격 증명 폐기 절차

## 한계와 확장 조건

- IAM 사용자는 장기 자격 증명 운영 부담이 있음
- 계정이 늘어나거나 학교·조직 계정과 연동해야 하면 IAM Identity Center가 더 적합
- 최소 권한 정책은 실제 plan·apply의 AccessDenied 기록을 바탕으로 좁혀가야 함
- CloudTrail 보존과 경보는 이번 역할 설계와 별도 운영 작업
