# 작업 기록

## 2026-09-09 — 인벤토리 범위 확장과 관리 경계 조사

### 배경

- 최초 킥오프에서는 단일 리전의 주요 자원 위주로 조회
- AWS 전체 프로젝트 편입을 위해 다른 리전·배포 권한·데이터 계층의 누락 여부 확인 필요

### 작업 1: 읽기 전용 조사 도구 확장

- `--all-regions` 옵션으로 활성 리전 자동 탐색
- 컨테이너·데이터·운영 서비스의 목록 조회 추가
- EC2 연결 역할의 관리형·인라인 정책 본문 조회
- S3 접근 제어·소유권·알림 설정, ECR 정책, Glue 테이블 요약 조회
- 계정 불일치 중단과 오류/부재 구분 회귀 검사 추가
- 커밋: `11a9d16` — 전체 리전 인벤토리와 IAM 및 저장소 상세 조회 추가

### 작업 2: 의존성 분석과 기록 체계

- 조회 결과와 저장소의 배포 워크플로·데이터 저장 경로 대조
- 추가 발견된 CI·외부 실행 주체의 IAM 권한 조사
- CloudFormation 관리 흔적과 SSM 관리 인스턴스 목록 추가 확인
- 프로젝트 전용, 기본·공유, 서비스·파이프라인 관리, 소유 불명 자원으로 분류
- 상세 응답·실제 식별자·소유 범위 표는 로컬 `docs/private/`에 기록
- 공개 작업 절차는 `docs/discovery-workflow.md`, 지속적인 기록·커밋 규칙은 `AGENTS.md`에 명시

### 검증

- Python 문법 검사 통과
- 회귀 테스트 4개 통과: 잘못된 계정 차단, 전체 활성 리전 선택, 권한 거절 처리, 선택 정책 부재 처리
- 실제 AWS 읽기 전용 조회 완료. 기본 조사와 추가 의존성 조사에서 미해결 조회 오류 없음
- 실제 자원 생성·수정·삭제·기동·import 미수행
- 커밋 전 운영 정보 파일의 Git 제외 여부와 공개 파일 내용 확인

### 판단과 한계

- 전용 인프라는 편입 후보, 공유·자동 생성 자원은 일괄 편입 보류
- 코드가 해당 AWS 자원을 참조한다는 사실은 현재 배포 성공을 입증하지 않음
- 조회한 서비스 내 결과와 계정 전체 자원 유무를 구분. 일부 서비스·하위 설정 및 팀 소유 관계 확인은 남아 있음
- 다음 단계: 공용 상태 저장소 설계 준비와 남은 소유·설정 확인 병행. 첫 EC2 편입 전에 관리 경계 확정

상세 조사 방법과 누락 범위는 [조사 절차](discovery-workflow.md) 참조.

## 2026-09-09 — 공용 상태 저장소 설계 및 계획 검증

### 배경과 결정

- 기존 자원 편입 전 공용 state·잠금·복원 기반 준비
- 사용자 결정: 우선 기존 AWS 로그인으로 준비, 팀 로그인·권한 연결은 추후 확정
- 전용 S3 버킷 하나에 bootstrap/project 상태 경로 분리

### 작업

- `bootstrap/state/`에 S3 버킷·버전 관리·공개 접근 차단·소유권·암호화·TLS 정책 정의
- backend 설정과 범위별 IAM 권한 템플릿 출력. 실제 주체에 권한을 연결하지 않음
- 처음은 local backend로 준비하고 버킷 생성 후 bootstrap state도 원격 이전하는 절차 설계
- 민감한 입력·계획·backend 파일은 로컬에 보관

### 검증 결과

- fmt 및 validate 통과
- Terraform 모의 테스트 1개 run 내 보호 조건 9개 통과
- 실제 AWS 계정으로 plan 실행: **6 to add, 0 to change, 0 to destroy**
- 이 결과는 S3 버킷 하나와 보호 설정 다섯 개에 대한 생성 계획
- 실제 버킷 생성·원격 상태 이전·실환경 잠금/복원 시험은 미수행

### 한계와 다음 작업

- plan 성공은 전역 버킷 이름의 사용 가능성이나 실제 쓰기 권한을 보장하지 않음
- 계획 적용 후 보호 설정 확인, bootstrap state 백업·원격 이전, project 연결 순으로 진행
- 동시 실행 잠금과 버전 복구는 별도 검증 key에서 시험 예정

설계 근거와 절차는 [상태 저장소 설계](state-backend.md) 참조.


## 2026-09-09 — 사용자 실행으로 S3 backend 활성화

### 실행과 확인 근거

- 사용자가 bootstrap 생성 계획 적용 후 `No changes` 출력 공유
- bootstrap에서 S3 backend 활성화 및 상태 이전 절차 수행 후 `No changes` 출력 공유
- S3 콘솔에서 bootstrap 상태 객체 확인을 사용자 보고로 확보
- project의 backend 초기화 후 실제 자원 변경 없이 출력값만 저장하는 plan 공유
- project 상태 저장 절차 이후 두 상태 객체가 모두 존재함을 사용자 확인
- 로컬에서 두 backend.tf 파일의 S3 backend 선언 확인

### 기록 범위

- 이 단계의 AWS 실행과 콘솔 확인은 사용자 수행. 에이전트가 S3 객체 내용이나 실제 잠금 동작을 재검증한 것은 아님
- project의 최종 `No changes` 출력은 별도로 전달받지 않음. 두 상태 객체 존재 확인과 구분
- bootstrap과 project의 backend 선언만 공개 코드에 포함
- 버킷·계정 등 실제 backend 값, state와 백업은 Git에서 제외
- 기존 EC2는 아직 조회용 data source이며 import 미수행

### 다음 작업

- 기존 state와 분리된 임시 key에서 동시 실행 잠금 및 버전 복원 시험
- 이후 모니터링 EC2 한 대의 변경 없는 import plan 준비


## 2026-09-09 — 사용자 실행으로 상태 잠금 시험

- 기존 상태와 분리한 verification key에서 Terraform 내장 terraform_data와 60초 대기 사용
- 사용자가 첫 apply 실행 중 두 번째 plan에서 상태 잠금 획득 오류 확인
- 첫 실행 완료 후 같은 plan에서 No changes 확인
- 결과: 사용자 실행 보고 기준 동시 접근 차단과 종료 후 잠금 해제 확인
- 실제 EC2 생성 없이 Terraform 내장 리소스의 테스트 상태만 기록
- 다음 단계의 S3 버전 복원용 로컬 스크립트 준비 및 Python 문법 검사 완료. 실행은 아직 미수행
- S3 객체 버전 복원과 Terraform state 복원 후 plan 검증은 구분해 기록


## 2026-09-09 — 사용자 실행으로 S3 객체 버전 복구 시험

### 실행과 근거

- 사용자가 로컬 recovery_probe.py를 실행해 PASS 출력 공유
- 에이전트가 생성된 로컬 Markdown 결과 파일을 읽어 단계별 성공 기록 확인
- Terraform 상태와 분리된 UUID별 테스트 객체에서 첫 내용 저장 → 두 번째 내용 저장 → 첫 버전 다운로드 → 새 최신 버전으로 재업로드 수행
- 복원된 최신 객체의 VersionId 및 내용 일치 확인 기록 확보
- 상세 버킷·key·VersionId는 비공개 로컬 기록에만 보관

### 결과와 한계

- S3 버전별 읽기와 이전 내용을 새 최신 버전으로 복원하는 절차 검증 완료
- 이전 작업의 Terraform 잠금 경쟁·해제 확인과 함께 상태 저장소의 기초 운영 검증 확보
- 실제 bootstrap/project/verification의 Terraform state 파일은 이번 복구 시험에서 수정하지 않음
- Terraform state의 lineage·serial 및 복원 후 plan 검증은 미수행. 전체 상태 복구 훈련 완료로 표현하지 않음
- 테스트 객체와 과거 버전은 보존 중

### 다음 작업

- 모니터링 EC2 한 대의 import 코드 초안 및 변경 없는 plan 준비
- import 적용 전 기존 의존 자원의 참조·소유 범위 확인
- Terraform state 자체의 복구 훈련은 별도 검증 대상으로 유지


## 2026-09-10 — 모니터링 EC2 import 계획 준비

- 사용자가 생성한 feat/import-monitoring-ec2 브랜치에서 작업
- 합의한 PR 기반 작업 흐름을 AGENTS.md에 기록. main 직접 푸시 및 자동 머지 금지
- AWS에서 import용 구성 초안을 읽기 전용 생성
- 자동 생성된 네트워크·IPv6 상충 옵션 및 계산 속성 정리
- 실제 속성은 비공개 monitoring_config 입력으로 분리, prevent_destroy 적용
- 실제 plan 결과: 1 to import, 0 to add, 0 to change, 0 to destroy
- plan JSON의 대상 ID·주소·무변경 조건 검사 PASS
- fmt·validate와 Python 회귀 테스트 9개 통과
- 공개 문서에는 실제 자원 식별자·설정값·plan 미포함
- 실제 apply는 미수행. PR 머지 후 사용자가 새 plan을 생성·검토하여 적용 예정

세부 구현 선택과 절차는 [모니터링 EC2 편입](import-monitoring.md) 참조.

## 2026-09-10 — 사용자 실행으로 모니터링 EC2 편입 완료

- PR #1 머지 후 사용자가 main에서 새 plan 생성·백업·apply 수행
- 사용자 보고 기준 최종 `No changes` 확인
- 원격 project state 목록에서 `aws_instance.monitoring` 등록을 읽기 전용으로 직접 확인
- 후속 보안 그룹 plan에서 `aws_instance.monitoring`이 import 대상 없이 `no-op`인 점을 추가 확인
- 기존 서버 재생성·기동·설정 변경 없이 Terraform state와 관리 주소 연결
- EC2 내부 애플리케이션·모니터링 서비스의 실행 상태를 확인한 결과는 아님

## 2026-09-10 — 모니터링 보안 그룹 import 계획 준비

- `feat/import-monitoring-security-group` 브랜치에서 작업
- 프로젝트 EC2의 그룹 연결, 대상 그룹의 ENI 연결, 다른 그룹의 참조 관계를 읽기 전용으로 조사
- 모니터링 전용 보안 그룹 1개, 인바운드 규칙 7개, 아웃바운드 규칙 1개를 개별 리소스로 정의
- 그룹 inline 규칙과 별도 규칙 리소스를 혼용하지 않도록 구성
- EC2가 관리되는 그룹 리소스를 참조하도록 변경하되 실제 그룹 ID 집합은 유지
- 최초 plan의 8개 update는 기존 무태그 규칙에 빈 태그를 지정한 표현 차이로 확인
- 무태그를 null로 반영하여 실제 변경 없이 최종 `9 to import, 0 to add, 0 to change, 0 to destroy` 확인
- plan JSON에서 검토한 주소·ID 9개와 기존 EC2를 포함한 다른 관리 자원의 무변경 조건 확인
- 단일 대상 검사기를 여러 import의 정확한 주소→ID 대응표 검사로 확장
- Terraform fmt·validate, Python 회귀 테스트 13개 통과
- 실제 import 적용은 미수행. PR 머지 후 main에서 새 plan을 생성해 사용자가 적용 예정
- 코드 커밋: `759a150` — 모니터링 보안 그룹과 규칙 import 구성 추가

세부 범위와 적용 절차는 [모니터링 보안 그룹 편입](import-monitoring-security-group.md) 참조.

## 2026-09-10 — 사용자 실행으로 모니터링 보안 그룹 편입 완료

### 실행과 확인 근거

- PR #2 머지 후 사용자가 main에서 새 plan 생성·state 백업·apply 수행
- 사용자 보고 기준 적용 후 후속 plan에서 `No changes` 확인
- 원격 project state를 읽기 전용으로 조회해 보안 그룹 1개, 인바운드 규칙 7개, 아웃바운드 규칙 1개의 관리 주소 등록 확인
- 기존 모니터링 EC2도 원격 state에 계속 등록되어 있음을 확인

### 결과와 한계

- 기존 보안 그룹과 규칙을 생성·수정·삭제하지 않고 Terraform 관리 대상으로 연결
- `No changes`로 코드·Terraform state·AWS 설정 사이에 관리 대상 기준 차이가 없음을 확인
- 실제 Grafana·Prometheus·Loki 요청이나 서버 내부 상태는 이번 작업에서 확인하지 않음
- 개별 규칙 방식이므로 Terraform에 등록하지 않은 외부 추가 규칙은 주기적인 목록 대조로 탐지 필요

### 다음 작업

- 모니터링 EC2가 사용하는 IAM 역할·인스턴스 프로파일·정책 연결 조사 및 변경 없는 import 계획 준비
- IAM 편입 이후 모니터링 관련 S3 자원으로 범위 확대

## 2026-09-10 — 모니터링 IAM import 계획 준비

### 배경과 범위

- 편입된 모니터링 EC2가 아직 문자열로 기존 인스턴스 프로파일을 참조하는 상태
- 당일 AWS 읽기 전용 재조회로 역할 1개, 프로파일 1개, 인라인 정책 2개, AWS 관리형 정책 연결 1개 확인
- 관리형 정책 자체는 AWS 소유이므로 역할과의 연결만 이번 관리 범위에 포함
- 기존 권한의 추가·축소 없이 현재 관계를 Terraform state에 연결하는 것을 목표로 설정

### 구현과 판단

- IAM 역할·프로파일·인라인 정책·관리형 정책 연결을 독립 리소스로 정의
- EC2의 프로파일 입력을 관리 리소스 참조로 전환하고 기존 값 일치 사전 조건 추가
- 실제 이름·ARN·신뢰 정책·권한 정책 본문을 Git 제외 로컬 tfvars로 분리
- 기존 정책 연결을 자동 회수하지 않도록 개별 연결 관리 방식 선택
- 역할·프로파일·정책·연결에 `prevent_destroy` 적용

### 트러블슈팅과 검증

- 역할과 프로파일이 같은 import 문자열을 사용하는 정상 구성을 기존 검사기가 중복으로 거절
- 동일 자원 유형 안에서만 import ID 중복을 차단하도록 검사기 수정
- 다른 자원 유형의 동일 ID를 허용하는 회귀 검사 추가
- 실제 plan: **5 to import, 0 to add, 0 to change, 0 to destroy**
- 기존 EC2·보안 그룹·규칙은 모두 `no-op`
- plan의 정확한 주소→ID 대응과 관리 자원 무변경 검사 통과
- Terraform fmt·validate, Python 회귀 테스트 14개 통과
- 구현 커밋: `9198966` — 모니터링 IAM 자원 import 구성 추가

### 한계와 다음 작업

- 실제 apply는 미수행. PR 머지 후 main에서 새 plan·state 백업·사용자 apply 필요
- 현재 권한의 최소 권한 충족 여부와 애플리케이션 AWS API 호출 성공은 미검증
- IAM 적용 완료 후 모니터링 관련 S3 자원 편입 준비

세부 관리 경계와 적용 절차는 [모니터링 IAM 편입](import-monitoring-iam.md) 참조.

## 2026-09-10 — 사용자 실행으로 모니터링 IAM 편입 완료

### 실행과 확인 근거

- PR #4 머지 후 머지된 main에서 새 plan 생성 및 import 대상 재검사
- 적용 직전 원격 project state를 Git 제외 로컬 파일로 백업하고 JSON 유효성·파일 권한 확인
- 사용자가 저장 plan을 적용하고 후속 plan의 `No changes` 결과 공유
- 원격 project state를 읽기 전용으로 조회해 IAM 역할·인스턴스 프로파일·인라인 정책 2개·관리형 정책 연결의 관리 주소 5개 등록 확인

### 결과와 한계

- 기존 IAM 권한과 연결을 추가·축소하지 않고 Terraform 관리 대상으로 연결
- `No changes`로 코드·Terraform state·실제 IAM 설정 사이에 관리 대상 기준 차이가 없음을 확인
- 실제 애플리케이션의 AWS API 호출 성공과 최소 권한 충족 여부는 이번 작업에서 확인하지 않음
- 개별 관리형 정책 연결 방식이므로 Terraform에 등록하지 않은 외부 연결은 주기적인 목록 대조로 탐지 필요

### 다음 작업

- 모니터링 관련 S3 버킷의 소유 범위와 현재 보호 설정 재확인
- 기존 버킷·보호 설정의 변경 없는 import 계획 준비

## 2026-09-10 — 모니터링 S3 import 계획 준비

### 배경과 범위

- 모니터링 구성에서 Loki의 로그 저장소로 사용하는 S3 버킷 확인
- 객체 key를 노출하지 않는 조회로 기존 객체가 존재하는 비어 있지 않은 버킷임을 확인
- 당일 AWS 읽기 전용 재조회로 버킷 본체와 암호화·공개 접근 차단·소유권 설정 확인
- 세부 설정 조회 결과는 비공개 기록으로 분리하고 버킷과 보호 설정 3개만 편입 대상으로 선정

### 구현과 판단

- 버킷 삭제 시 객체까지 지우지 않도록 `force_destroy = false` 적용
- 버킷과 보호 설정에 `prevent_destroy` 적용
- 실제 버킷 이름과 태그를 Git 제외 로컬 tfvars로 분리
- 버전 관리 활성화는 현재 상태를 바꾸지 않는 최초 import 원칙에 따라 제외하고 별도 개선으로 분리
- 정책·수명 주기·CORS·웹 호스팅·복제·객체 잠금 등 선택 설정은 최초 편입 범위에서 제외

### 검증

- 실제 plan: **4 to import, 0 to add, 0 to change, 0 to destroy**
- 기존 EC2·보안 그룹·규칙·IAM 자원 15개는 모두 `no-op`
- plan의 정확한 주소→ID 대응과 관리 자원 무변경 검사 통과
- Terraform fmt·validate, Python 회귀 테스트 14개 통과
- 구현 커밋: `45f80b5` — 모니터링 S3 자원 import 구성 추가

### 한계와 다음 작업

- 실제 apply와 Loki의 S3 읽기·쓰기 검증은 미수행
- 기존 객체의 암호화 상태와 삭제 복구 가능성은 이번 plan으로 확인되지 않음
- PR 머지 후 main에서 새 plan·state 백업·사용자 apply 필요
- 적용 완료 후 버전 관리·보존 정책 개선 또는 나머지 EC2 편입 진행

세부 범위와 적용 절차는 [모니터링 S3 편입](import-monitoring-s3.md) 참조.

## 2026-09-11 — 사용자 실행으로 모니터링 S3 편입 완료

### 실행과 확인 근거

- PR #6 머지 후 머지된 main에서 새 plan 생성 및 import 대상 재검사
- 적용 직전 원격 project state를 Git 제외 로컬 파일로 백업하고 JSON 유효성·파일 권한 확인
- 사용자가 저장 plan을 적용하고 후속 plan의 `No changes` 결과 공유
- 원격 project state를 읽기 전용으로 조회해 버킷 본체·암호화·공개 접근 차단·소유권 설정의 관리 주소 4개 등록 확인

### 결과와 한계

- 기존 버킷·객체·보호 설정을 수정하거나 삭제하지 않고 Terraform 관리 대상으로 연결
- `No changes`로 코드·Terraform state·실제 S3 설정 사이에 관리 대상 기준 차이가 없음을 확인
- Loki의 실제 S3 읽기·쓰기와 기존 객체의 암호화·복구 가능성은 이번 작업에서 확인하지 않음
- 최초 편입 범위 밖의 선택 설정은 주기적인 AWS 설정 목록 대조 필요

### 다음 작업

- 다음 EC2 대상과 연결 보안 그룹·IAM·스토리지의 소유 범위 조사
- 변경 없는 편입을 계속 진행하고 버전 관리·보존 정책은 별도 운영 개선으로 분리

## 2026-09-11 — Airflow EC2 편입 계획 준비

### 대상 선정

- GraphDB EC2는 담당자 보안 조치 이슈로 분리하고 Terraform Draft PR을 대기 상태로 유지
- 남은 Airflow EC2와 파이프라인 테스트 EC2의 상태·의존성·프로젝트 문서상 사용 근거 비교
- 크롤링과 데이터 파이프라인을 조율하는 메인 서버로 문서화된 Airflow EC2를 다음 대상으로 선정
- 대상은 현재 중지 상태이며 import로 시작하지 않음

### 구현과 트러블슈팅

- AWS API에서 user data 존재 여부를 원문 출력 없이 먼저 확인하고 비어 있음을 확인
- 자동 생성 코드의 네트워크 인터페이스와 일반 네트워크 속성 충돌 제거
- IPv6 주소 수와 주소 목록 충돌을 주소 목록만 유지하는 방식으로 해결
- 실제 속성은 Git 제외 `airflow_config` 입력으로 분리
- 연결 보안 그룹·IAM은 기존 ID·이름 참조 유지, 루트 EBS는 EC2 블록에서만 관리
- `prevent_destroy` 적용

### 검증과 한계

- 실제 plan: **1 to import, 0 to add, 0 to change, 0 to destroy**
- 예상 import 주소·ID 일치, 기존 관리 자원 무변경, Airflow user data 비어 있음 확인
- Terraform fmt·validate와 Python 회귀 테스트 14개 통과
- 실제 import는 미수행. PR 머지 후 main에서 새 plan과 state 백업을 만들어 사용자 적용 필요
- Airflow UI·Scheduler·DAG와 내부 데이터는 중지 상태이므로 이번 EC2 속성 편입에서 검증하지 않음

세부 범위와 적용 절차는 [Airflow EC2 편입](import-airflow-ec2.md) 참조.

## 2026-09-11 — 사용자 실행으로 Airflow EC2 편입 완료

### 실행과 확인 근거

- PR #9 머지 후 원격 main 동기화
- 머지된 main에서 새 import plan 생성 및 예상 주소·ID 재검사
- 적용 전 원격 project state를 Git 제외 로컬 파일로 백업하고 JSON 유효성·파일 권한 확인
- 사용자가 저장 plan을 적용하고 후속 plan의 `No changes` 결과 공유
- 원격 project state 목록에서 `aws_instance.airflow` 등록을 읽기 전용으로 직접 확인
- 기존 모니터링 EC2와 종속 자원도 state에 계속 등록되어 있음을 확인

### 결과와 한계

- 기존 Airflow EC2를 생성·수정·시작하지 않고 Terraform 관리 대상으로 연결
- 코드·state·AWS의 관리 대상 속성이 일치하여 후속 변경 없음 확인
- EC2는 기존 중지 상태이며 Airflow UI·Scheduler·DAG와 내부 데이터는 검증하지 않음
- 연결된 보안 그룹·IAM은 아직 기존 ID·이름 참조 상태

### 구현 방식 구분

- HCL의 import 블록과 `aws_instance.airflow` 리소스가 실제 관리 관계 선언
- Terraform AWS provider가 AWS를 조회하고 import 결과를 원격 state에 저장
- Python 도구는 plan JSON의 예상 import와 변경 없음 검증에만 사용하며 AWS 자원을 관리하지 않음

### 다음 작업

- Airflow 전용 보안 그룹·규칙과 IAM 역할·정책 연결의 소유 범위 조사
- 종속 자원의 변경 없는 import 계획 준비

## 2026-09-11 — Airflow 보안 그룹 import 계획 준비

### 범위 조사

- Airflow EC2에 연결된 보안 그룹 2개와 규칙·네트워크 인터페이스 관계를 AWS에서 읽기 전용으로 재조회
- Airflow 전용 그룹은 네트워크 인터페이스 한 개에만 연결됨을 확인
- 공용 SSH 그룹은 프로젝트 EC2 네 대가 공유하므로 이번 편입에서 제외
- 전용 그룹 1개, 인바운드 규칙 3개, 아웃바운드 규칙 1개를 편입 대상으로 선정
- 외부 접근 범위가 넓은 기존 규칙은 최초 편입에서 유지하고 별도 보안 개선 대상으로 기록

### 구현과 트러블슈팅

- 보안 그룹과 규칙을 별도 리소스로 정의하고 inline rule 혼용 방지
- Airflow EC2가 관리 그룹을 참조하도록 전환하되 기존 그룹 ID 집합 유지
- 실제 ID·규칙 소스는 Git 제외 로컬 tfvars로 분리
- 그룹 연결 precondition, 규칙 소스 입력 검증, `prevent_destroy` 적용
- 최초 plan의 update 1건을 전체 프로토콜 규칙 포트의 `-1`과 provider 정규화 값 `null` 차이로 확인
- 전체 프로토콜 규칙의 포트를 `null`로 수정해 불필요한 변경 제거

### 검증과 한계

- 최종 plan: **5 to import, 0 to add, 0 to change, 0 to destroy**
- 예상 주소→ID 대응과 기존 관리 자원 무변경 검사 통과
- Terraform fmt·validate, Python 회귀 테스트 14개 통과
- 실제 import는 미수행. PR 머지 후 main에서 새 plan·state 백업·사용자 apply 필요
- 보안 정책 적정성, Airflow 애플리케이션 통신과 인증 상태는 이번 편입에서 검증하지 않음

세부 범위와 적용 절차는 [Airflow 보안 그룹 편입](import-airflow-security-group.md) 참조.

## 2026-09-11 — 사용자 실행으로 Airflow 보안 그룹 편입 완료

### 실행과 확인 근거

- PR #11 머지 후 원격 main 동기화
- 머지된 main에서 적용 전 원격 project state를 Git 제외 로컬 파일로 백업
- 새 plan에서 `5 to import, 0 to add, 0 to change, 0 to destroy` 재확인
- 예상 import 주소·ID 대응과 기존 관리 자원 무변경 검사 통과
- 사용자가 저장 plan을 적용하고 예상 결과 확인
- 원격 state 목록에서 Airflow 전용 보안 그룹 1개와 인바운드 규칙 3개·아웃바운드 규칙 1개 등록 확인
- 적용 후 후속 plan에서 `No changes` 확인

### 결과와 한계

- 기존 통신 규칙을 생성·수정·삭제하지 않고 Terraform 관리 대상으로 연결
- Airflow EC2가 관리 보안 그룹 리소스를 참조하며 기존 연결 그룹 집합 유지
- 원격 state·코드·AWS의 관리 대상 속성 일치 확인
- Airflow 서비스가 중지 상태이므로 UI·Scheduler·DAG 통신은 이번 작업에서 검증하지 않음
- 기존 외부 접근 범위와 인증 방식은 별도 보안 개선 필요

### 다음 작업

- Airflow IAM 역할·인스턴스 프로파일·정책 연결의 소유 범위 조사
- 현재 권한을 바꾸지 않는 import 계획 준비

## 2026-09-11 — Airflow IAM import 계획 준비

### 범위 조사

- Airflow EC2에 연결된 인스턴스 프로파일과 IAM 역할을 AWS에서 읽기 전용으로 재조회
- 역할과 프로파일이 1:1로 연결되고 해당 프로파일을 사용하는 EC2가 Airflow 서버 한 대뿐임을 확인
- 인라인 정책 없이 AWS 관리형 정책 연결 5개로 권한이 구성됨을 확인
- 역할 1개, 인스턴스 프로파일 1개, 관리형 정책 연결 5개를 편입 대상으로 선정

### 구현과 판단

- IAM 역할·인스턴스 프로파일·관리형 정책 연결을 독립 Terraform 리소스로 정의
- Airflow EC2의 프로파일 입력을 관리 리소스 참조로 전환하고 기존 값 일치 precondition 추가
- 실제 이름·ARN·신뢰 정책을 Git 제외 로컬 tfvars로 분리
- 정책 연결을 개별 관리해 최초 편입 중 의도하지 않은 권한 회수 방지
- 모든 편입 자원에 `prevent_destroy` 적용
- 신뢰 정책 JSON 유효성 검사와 관리형 정책 ARN 중복 입력 차단

### 검증과 한계

- 실제 plan: **7 to import, 0 to add, 0 to change, 0 to destroy**
- 예상 IAM 주소·ID 대응과 기존 관리 자원 무변경 검사 통과
- Terraform fmt·validate와 Python 회귀 테스트 14개 통과
- 구현 커밋: `51152d4` — Airflow IAM 자원 import 구성 추가
- 현재 관리형 정책의 최소 권한 충족 여부와 Airflow의 AWS API 호출 성공은 미검증
- 실제 사용 기록을 근거로 한 권한 축소는 별도 운영 변경으로 진행 필요

세부 관리 경계와 적용 절차는 [Airflow IAM 편입](import-airflow-iam.md) 참조.

## 2026-09-12 — 사용자 실행으로 Airflow IAM 편입 완료

### 실행과 확인 근거

- PR #13 머지 후 원격 main 동기화
- 적용 전 원격 project state를 Git 제외 로컬 파일로 백업
- 머지된 main의 새 plan에서 `7 to import, 0 to add, 0 to change, 0 to destroy` 재확인
- 예상 IAM 주소·ID 대응과 기존 관리 자원 무변경 검사 통과
- 사용자가 저장 plan을 적용하고 예상 결과 확인
- 원격 state 목록에서 IAM 역할 1개·인스턴스 프로파일 1개·관리형 정책 연결 5개 등록 확인
- 적용 후 후속 plan에서 `No changes` 확인

### 결과와 한계

- 기존 역할과 권한 연결을 추가·축소하지 않고 Terraform 관리 대상으로 연결
- Airflow EC2가 관리 인스턴스 프로파일 리소스를 참조하며 기존 연결 유지
- 코드·원격 state·AWS의 관리 대상 IAM 설정 일치 확인
- 실제 Airflow DAG의 AWS API 호출 성공과 현재 권한의 최소 권한 충족 여부는 이번 작업에서 검증하지 않음
- 넓은 범위의 관리형 정책은 사용 기록을 확보한 뒤 별도 운영 개선으로 축소 필요

### 다음 작업

- 논문 크롤링 EC2의 현재 사용 여부·소유 범위·종속 자원 조사
- 조사 결과에 따라 편입 또는 폐기 후보로 분류

## 2026-09-12 — 논문 크롤링 EC2 편입 가치 조사

### 확인 범위

- 현재 EC2 상태·생성 시점·중지 기록·네트워크·IAM·디스크·user data를 AWS에서 읽기 전용으로 조회
- 최근 감사 이벤트에서 시작·중지·재부팅·종료 기록 검색
- 전체 프로젝트 저장소에서 서버 이름과 파이프라인 테스트 서버 참조 검색
- 연결 보안 그룹의 다른 네트워크 인터페이스 사용 범위 확인
- 루트 볼륨과 자체 스냅샷 존재 여부 확인

### 확인 결과

- 로컬 컴퓨터를 계속 켜두기 어려운 장시간 화장품 성분 논문 크롤링을 위해 생성한 서버
- 크롤링 작업 이후 장기간 중지 상태이며 향후 재사용 여부는 미확정
- 프로젝트 문서와 코드에 해당 EC2의 생성·배포·복구 절차가 없음
- IAM 인스턴스 프로파일, 공인 IP, user data 없음
- 루트 볼륨 하나만 연결되어 있고 별도 자체 스냅샷 없음
- 연결 보안 그룹은 프로젝트 EC2 여러 대가 공유하므로 해당 서버 전용 자원이 아님
- 감사 이벤트 조회 결과는 없었으나 조회 보존 범위 밖의 과거 활동까지 부재함을 뜻하지는 않음

### 판단과 한계

- 상시 운영 서비스가 아닌 필요할 때 실행하는 배치 작업 환경이므로 기존 EC2의 Terraform 편입 보류
- 서버 내부에 문서화되지 않은 코드·설정·데이터가 있을 가능성은 읽기 전용 외부 조회만으로 배제할 수 없음
- 재사용 시 현재 서버를 장기 보존하기보다 Terraform으로 재생성 가능한 EC2와 컨테이너 기반 크롤러 구성 권장
- 결과와 체크포인트는 서버 수명과 분리해 영구 저장소에 보관하는 구조 필요
- 현재 서버를 그대로 재사용하면 내부 상태 확인 후 import 검토, 사용 종료이면 백업 필요성 확인 후 별도 정리 계획 수립
- 이번 조사에서는 AWS 자원을 생성·수정·시작·삭제하지 않음

세부 판단 기준은 [논문 크롤링 EC2 관리 판단](assess-pipeline-ec2.md) 참조.

## 2026-09-12 — Terraform 상태 복구 및 plan 검증

### 목적과 시험 구성

- 일반 S3 객체 복구에서 나아가 Terraform state의 과거 버전을 실제로 복원하고 Terraform이 이를 읽는지 확인
- 운영 bootstrap/project 상태와 분리된 고유 verification key 사용
- 실제 AWS 자원을 만들지 않는 `terraform_data`에 `first`와 `second` 값을 순서대로 저장해 정상 상태 A와 문제 상황을 가정한 최신 상태 B 구성

### 사용자 실행과 확인 근거

- 상태 A 적용 후 같은 입력의 plan에서 `No changes` 확인
- 상태 B 적용 후 같은 입력의 plan에서 `No changes` 확인
- 두 상태의 S3 VersionId가 서로 다름을 사용자 실행으로 확인
- 로컬 검증으로 A와 B의 lineage 일치, serial 1에서 2로 증가, 값이 각각 `first`와 `second`임을 확인
- A의 S3 버전을 같은 key의 새 최신 버전으로 복원
- 구성은 `second`로 유지한 plan에서 `first → second`, **0 to add, 1 to change, 0 to destroy** 확인
- 해당 변경 계획은 적용하지 않고 B의 기존 버전을 새 최신 버전으로 재복원
- 사용자 실행 최종 plan에서 `No changes` 확인

### 결과와 한계

- S3 과거 상태 복원, Terraform의 복원 상태 인식과 차이 계산, 시험 전 상태 원상 복귀까지 확인
- 기존 버전을 삭제하거나 운영 상태 key를 수정하지 않음
- 실제 EC2·데이터·AWS provider 자원의 생성·변경·삭제 없음
- 상태 복구는 실제 인프라와 데이터를 복구하지 않으므로 자원별 백업 전략이 별도로 필요
- 팀 로그인 방식과 최소 권한 정책 확정 후 팀원별 상태 읽기·잠금·plan 검증 필요

단계별 의미와 실제 장애 적용 순서는 [Terraform 상태 복구 검증](verify-state-recovery.md) 참조.

## 2026-09-11 — GraphDB EC2 편입 준비와 보안 게이트

### 대상 선정과 구현

- 실행 중인 핵심 데이터 서비스인 GraphDB를 편입 대상으로 선정
- 자동 생성 구성에서 네트워크 인터페이스·IPv6 상충 속성과 계산값 정리
- 실제 EC2 설정은 Git 제외 `graphdb_config` 입력으로 분리
- 보안 그룹·IAM은 현재 ID·이름 참조를 유지하고 루트 EBS는 EC2 블록에서만 관리
- `prevent_destroy` 적용, 기존 user data는 공개 코드와 tfvars에 복사하지 않도록 제외

### 검증과 발견

- 실제 AWS 계획에서 `1 to import, 0 to add, 0 to change, 0 to destroy` 확인
- 기존 user data에 사용자 계정 생성 정보와 자격 정보가 포함되어 plan에 노출되는 문제 발견
- AWS 변경 0건 여부와 별개로 민감 정보가 Terraform state에 저장될 수 있어 현재 plan 적용 중단
- EC2 import 대상의 `user_data`가 비어 있지 않으면 실패하는 검사 추가
- 보안 검사 회귀 테스트를 포함한 Python 테스트 15개 통과

### 한계와 다음 작업

- 실제 import는 수행하지 않았으며 기존 서버와 AWS 설정은 변경하지 않음
- 자격 정보 교체, 불필요한 계정·키 제거, EC2 중지 후 user data 삭제 필요
- 재시작 후 Neo4j와 추천 서비스 조회 검증, 새 import plan 검사 통과 후 편입 진행
- GraphDB 전용 보안 그룹·IAM 편입은 EC2 편입 완료 뒤 별도 작업으로 진행
- GraphDB-Server의 Docker Compose 구성과 앱 `/health` 동작을 확인해 사전 점검, EC2 중지·스냅샷, user data 삭제, 서비스 검증, Terraform 재검증 순서의 실행 절차 보강
- GraphDB가 다른 팀원의 운영 범위이고 확인된 HTTP 주소만으로는 EC2 SSH 관리가 불가능해 직접 변경하지 않기로 결정
- GraphDB-Server 이슈 #5에 자격 정보 교체, user data 삭제, 재시작 후 검증 작업을 인계
- Terraform Draft PR #8에 이슈 #5를 선행 조건으로 연결하고 완료 전 머지·apply 금지 명시

세부 판단과 적용 선행 조건은 [GraphDB EC2 편입](import-graphdb-ec2.md) 참조.

## 2026-09-12 — GraphDB 보안 조치와 import 재검증

### 문제와 대응

- 최초 import 계획에서 EC2 user data의 자격 정보가 Terraform plan과 state에 저장될 수 있어 적용 차단
- 공개 저장소의 적재 스크립트에서도 기존 Neo4j 비밀번호를 로그에 출력하는 문제 확인
- 새 임의 비밀번호로 Neo4j 사용자, 서버·로컬 환경 파일과 GitHub Actions secret 갱신
- 서버 환경 파일 권한을 `600`으로 제한하고 적재 로그의 비밀번호 출력 제거
- SSH 비밀번호 로그인을 끄고 사용자 홈의 개인키 두 개를 root 전용 위치로 격리
- 공개키가 등록된 팀 계정의 기존 로컬 비밀번호 잠금

### 중단 작업과 복구 근거

- Neo4j와 Promtail을 정상 종료한 뒤 EC2 중지
- 중지된 루트 볼륨의 EBS 스냅샷 생성 완료
- EC2 user data를 12,184바이트에서 0바이트로 변경
- EC2 재시작 후 시스템 상태 검사, 공개키 SSH 설정, Neo4j와 Promtail 실행 확인
- 추천 서버 설정으로 GraphDB 인증과 읽기 쿼리 수행
- 재시작 전후 그래프 노드·관계 수 일치 확인

### Terraform 재검증

- 오래된 GraphDB 브랜치를 최신 main에 rebase하며 Airflow·상태 복구 문서와 구성 통합
- `terraform fmt -check -recursive`, `terraform validate`, Python 회귀 테스트 15개 통과
- 새 실제 계획: **1 to import, 0 to add, 0 to change, 0 to destroy**
- 계획 검사기에서 GraphDB EC2의 빈 user data, 정확한 import 주소·ID와 기존 관리 자원 무변경 확인
- PR 병합 후 `main`에서 계획을 새로 생성하고 적용 직전 원격 state 백업 완료
- 사용자 적용 결과: **1 imported, 0 added, 0 changed, 0 destroyed**
- 적용 후 `aws_instance.graphdb`의 원격 state 등록 확인
- 같은 입력으로 다시 실행한 plan에서 **No changes** 확인

### 한계와 다음 작업

- 복구 스냅샷은 기존 루트 볼륨과 같이 암호화되지 않음
- 관리자 공개키 접속은 검증했으나 팀원별 사용자 계정의 공개키 접속은 각 장비에서 추가 확인 필요
- EC2 본체 편입은 완료됐으며 전용 보안 그룹·규칙과 IAM 역할·프로파일·정책 연결은 별도 편입 필요

## 2026-09-13 — GraphDB 보안 그룹과 IAM 편입 준비

### 범위 결정

- GraphDB EC2의 전용 보안 그룹과 기존 규칙을 편입 대상으로 선정
- 여러 EC2가 공유하는 SSH 보안 그룹은 GraphDB 단독 범위가 아니므로 제외
- IAM 역할·인스턴스 프로파일·팀 관리형 정책·기존 정책 연결을 함께 편입
- 실제 ID와 정책 문서는 Git 제외 로컬 변수 파일로 분리

### 구현과 검증

- EC2의 전용 보안 그룹과 인스턴스 프로파일을 새 Terraform 자원 참조로 전환
- 보안 그룹 규칙을 ingress·egress 독립 자원으로 모델링
- 팀 관리형 정책 문서와 AWS 관리형 정책 연결을 각각 명시
- 연결 대상 일치 사전 조건, 입력 유효성 검사와 `prevent_destroy` 적용
- 최초 plan에서 빈 태그 맵 명시로 규칙 3건의 차이 발견 후 입력 수정
- 최종 실제 plan: **10 to import, 0 to add, 0 to change, 0 to destroy**
- 계획 검사기에서 정확한 import 집합과 기존 관리 자원 무변경 확인

### 한계와 다음 작업

- 현행 구성 편입과 접근·권한 최소화 작업을 분리
- PR 병합 후 새 plan과 state 백업 생성 완료
- 사용자 apply 결과: **10 imported, 0 added, 0 changed, 0 destroyed**
- 보안 그룹·규칙과 IAM 자원 10건의 원격 state 등록 확인
- 적용 후 후속 plan에서 **No changes** 확인
- 적용 후 공용 SSH 보안 그룹의 관리 범위와 네트워크 접근 개선 검토

세부 설계와 검증 절차는 [GraphDB 연결 자원 Terraform 편입](import-graphdb-dependencies.md) 참조.

## 2026-09-13 — 공용 SSH 보안 그룹 편입 준비

### 소유 범위와 설계

- 여러 프로젝트 EC2가 공유하는 보안 그룹을 서버별 전용 구성에서 분리해 공용 자원으로 정의
- 관리 중인 모니터링·Airflow·GraphDB EC2의 기존 그룹 ID를 Terraform 자원 참조로 전환
- 편입 보류 중인 파이프라인 EC2의 현재 연결은 유지
- 현행 규칙 편입과 접근 범위 축소를 별도 변경으로 분리

### 구현과 검증

- 보안 그룹 본체와 ingress·egress 규칙을 독립 자원으로 모델링
- 관리 중인 세 EC2에 기존 그룹이 연결됐는지 확인하는 사전 조건 추가
- 실제 값은 Git 제외 로컬 변수 파일에 보관하고 모든 자원에 `prevent_destroy` 적용
- `terraform fmt -check -recursive`, `terraform validate`, Python 테스트 15개 통과
- 최종 실제 plan: **3 to import, 0 to add, 0 to change, 0 to destroy**
- 계획 검사기에서 정확한 import 3건과 기존 관리 자원 무변경 확인

### 다음 작업

- PR 병합 후 새 plan과 state 백업 생성 완료
- 사용자 apply 결과: **3 imported, 0 added, 0 changed, 0 destroyed**
- 공용 그룹 본체와 규칙 2건의 원격 state 등록 확인
- 적용 후 후속 plan에서 **No changes** 확인
- 적용 후 Tailscale·팀원별 공개키 접속 근거를 확보하고 SSH 접근 범위 개선

세부 설계와 적용 절차는 [프로젝트 공용 SSH 보안 그룹 편입](import-shared-ssh-security-group.md) 참조.

## 2026-09-16 — GraphDB 공개 SSH 경로 분리 준비

### 접속 경로 조사

- 프로젝트 EC2가 모두 중지 상태이며 SSM 관리 대상이 없음을 확인
- Tailscale에는 GraphDB와 모니터링 노드가 등록되어 있고 Airflow·파이프라인은 확인되지 않음
- 단계적 변경 대상으로 기존 RSA 키 접속이 가능한 GraphDB를 우선 선정
- GraphDB를 잠시 시작해 Tailscale SSH, 접속 계정과 관리자 권한 확인 후 다시 중지

### 계획 차단과 수정

- 최초 plan에서 동적 공인 IP 연결 상태 차이로 GraphDB EC2 교체 제안 발견
- `prevent_destroy`가 교체를 차단해 실제 AWS 변경 없음
- 중지·시작에 따라 달라지는 공인 IP 관측값을 수명 주기 비교에서 제외하고 삭제 방지 유지
- 공용 SSH 그룹 하나만 제거하고 GraphDB 전용 그룹을 유지하도록 구성

### 검증

- 정확한 보안 그룹 제거만 허용하는 계획 검사기와 테스트 추가
- `terraform fmt -check -recursive`, `terraform validate`, Python 테스트 20개 통과
- 최종 plan: **0 to add, 1 to change, 0 to destroy**
- GraphDB 시작·중지 검증 후 재생성한 plan에서도 동일 결과 확인

### 다음 작업

- PR 병합 후 새 plan과 state 백업 생성 완료
- 사용자 apply 결과: **0 added, 1 changed, 0 destroyed**
- GraphDB 전용 보안 그룹만 연결된 상태와 공용 SSH 경로 차단 확인
- Tailscale RSA SSH 새 세션과 관리자 권한 재검증
- GraphDB를 기존 중지 상태로 복구하고 후속 plan에서 **No changes** 확인
- 모니터링·Airflow·파이프라인은 대체 접속 경로를 확보한 뒤 별도 변경

세부 근거와 적용 게이트는 [GraphDB 공개 SSH 경로 단계적 제거](harden-graphdb-ssh.md) 참조.

## 2026-09-16 — Airflow 공개 SSH 경로 분리 준비

### SSM 관리 경로 검증

- Airflow를 시작해 SSM Agent가 온라인 관리 노드로 등록됨을 확인
- 첫 명령은 일반 패키지 서비스 이름을 조회해 실패했으나 root 명령 실행과 응답은 확인
- Ubuntu Snap 서비스 단위로 수정한 진단 명령 성공
- SSM root 명령 채널과 Agent 활성 상태를 확인한 뒤 Airflow를 기존 중지 상태로 복구

### 구현과 검증

- Airflow EC2의 공용 SSH 그룹 참조 제거, 전용 그룹 유지
- GraphDB 작업에서 추가한 계획 검사기를 재사용해 정확한 그룹 하나의 제거만 허용
- `terraform fmt -check -recursive`, `terraform validate`, Python 테스트 20개 통과
- 최종 plan: **0 to add, 1 to change, 0 to destroy**
- Airflow 외 관리 자원 변경 없음 확인

### 다음 작업

- PR 병합 후 새 plan과 state 백업 생성 완료
- 사용자 apply 결과: **0 added, 1 changed, 0 destroyed**
- Airflow 전용 보안 그룹만 연결된 상태와 공용 SSH 경로 차단 확인
- SSM Agent 온라인과 root 명령 채널 재검증
- Airflow를 기존 중지 상태로 복구하고 후속 plan에서 **No changes** 확인

세부 근거와 적용 게이트는 [Airflow 공개 SSH 경로 단계적 제거](harden-airflow-ssh.md) 참조.

## 2026-09-16 — 모니터링 SSM 관리 경로 준비

### 배경과 선택

- 모니터링 Tailscale 노드는 확인됐지만 현재 작업 장비의 지속 가능한 SSH 키 접속은 미확인
- Ubuntu 24.04 기반 EC2와 IAM 인스턴스 프로파일은 있으나 SSM 정책 연결 없음
- 공개 SSH 제거보다 SSM 관리 경로 추가와 실제 검증을 먼저 수행하기로 결정

### 구현과 검증

- 모니터링 IAM 역할에 AWS 관리형 SSM Core 정책 연결을 Terraform 자원으로 추가
- 정확한 역할·정책 연결 한 건의 생성만 허용하는 plan 검사기와 테스트 추가
- `terraform fmt -check -recursive`, `terraform validate`, Python 테스트 25개 통과
- 최종 실제 plan: **1 to add, 0 to change, 0 to destroy**
- 기존 관리 자원 변경 없음 확인

### 다음 작업

- PR 병합 후 새 plan과 state 백업 생성 완료
- 사용자 apply 결과: **1 added, 0 changed, 0 destroyed**
- IAM 정책 연결과 SSM Agent `Online` 확인
- SSM 원격 명령 `Success`, 종료 코드 0, 실행 사용자 `root` 확인
- 모니터링을 기존 중지 상태로 복구하고 후속 plan에서 **No changes** 확인
- 별도 PR에서 공용 SSH 그룹 연결 제거 예정

세부 설계와 적용 절차는 [모니터링 서버 SSM 관리 경로 추가](enable-monitoring-ssm.md) 참조.

## 2026-09-16 — 모니터링 공개 SSH 경로 분리 준비

### 선행 조건

- 모니터링 SSM 정책 연결과 Agent `Online` 확인 완료
- SSM 원격 root 명령 성공과 기존 중지 상태 복구 완료
- 공개 SSH 제거 후 사용할 독립적인 관리·복구 경로 확보

### 구현과 검증

- 모니터링 EC2에서 공용 SSH 보안 그룹 참조 제거
- 모니터링 전용 보안 그룹 유지
- 기존 보안 그룹 분리 계획 검사기로 대상과 그룹 집합을 검증
- `terraform fmt -check -recursive`, `terraform validate`, Python 테스트 25개 통과
- 최종 plan: **0 to add, 1 to change, 0 to destroy**
- 모니터링 외 관리 자원 변경 없음 확인

### 다음 작업

- PR 병합 후 새 plan과 state 백업 생성 완료
- 사용자 apply 결과: **0 added, 1 changed, 0 destroyed**
- 전용 보안 그룹 하나만 연결되고 TCP 22 인바운드 규칙이 없는 상태 확인
- SSM Agent `Online`과 원격 root 명령 재검증 성공
- 서버를 기존 중지 상태로 복구하고 후속 plan에서 **No changes** 확인
- 파이프라인 서버의 관리 경로와 장기 보존 여부 검토 예정

세부 근거와 적용 게이트는 [모니터링 공개 SSH 경로 단계적 제거](harden-monitoring-ssh.md) 참조.

## 2026-09-17 — 논문 크롤링 EC2 폐기와 공용 SSH 정리 준비

### 폐기 판단

- 일회성 장시간 논문 크롤링 이후 장기간 중지된 테스트 서버
- 전용 IAM·별도 데이터 볼륨·자동 실행 구성 없음
- 기존 서버를 계속 보존하거나 Terraform에 편입하지 않고 재생성 가능한 배치 구조로 전환하기로 결정

### 백업과 폐기

- 서버가 중지 상태이고 종료 방지가 비활성화된 상태 확인
- 비공개 복구용 AMI 생성 후 `available` 확인
- 연결된 루트 스냅샷 `completed 100%` 확인
- EC2 종료와 기존 `DeleteOnTermination` 루트 볼륨 삭제 확인
- AMI 복원 부팅 시험과 보존 기한 결정은 후속 과제로 기록

### 공용 SSH 자원 정리

- 파이프라인 종료 후 공용 SSH 그룹을 사용하는 네트워크 인터페이스 0개 확인
- 그룹 본체와 인바운드·아웃바운드 규칙을 Terraform 구성에서 제거
- 정확한 삭제 대상 집합만 허용하는 plan 검사기와 테스트 5개 추가
- 전체 Python 테스트 30개 통과
- 실제 plan: **0 to add, 0 to change, 3 to destroy**
- 세 삭제 대상 외 다른 관리 자원 변경 없음 확인

### 적용 결과

- PR 병합 후 원격 state 백업과 연결 대상 0개 재확인
- 사용자 apply 결과: **0 added, 0 changed, 3 destroyed**
- AWS에서 공용 SSH 그룹 삭제 확인
- Terraform state에서 그룹과 규칙 주소 제거 확인
- 후속 plan에서 **No changes** 확인

세부 결과와 적용 게이트는 [논문 크롤링 EC2 안전 폐기](retire-pipeline-ec2.md) 참조.

## 2026-09-17 — 파이프라인 백업 보존 기한 설정

- 폐기 전 생성한 복구용 AMI와 스냅샷의 초기 보존 기간을 30일로 결정
- 재검토일을 **2026-10-17**로 설정
- 두 자원에 재검토일과 삭제 전 검토 태그 적용
- 자동 삭제는 설정하지 않고 재검토일에 복원 필요성과 사용 관계를 확인한 뒤 결정
- 실제 삭제 시 AMI 등록 해제 후 연결 스냅샷 삭제 순서 적용

## 2026-09-17 — 팀 Terraform 접근 구조 설계

### 확인 결과

- 초기 단일 계정과 소규모 팀 운영을 기준으로 설계
- 실제 로그인 주체, 사용자 목록과 MFA 등록 현황은 비공개 기록으로 분리

### 설계 선택

- 초기 단계에서는 Identity Center 도입보다 개별 IAM 사용자와 MFA 기반 역할 전환 사용
- 팀원은 project state 읽기·잠금·AWS 조회가 가능한 계획 역할 사용
- 실제 project state 쓰기와 인프라 변경은 지정 관리자용 적용 역할로 분리
- bootstrap state 복구와 상태 버킷 관리는 별도 비상 관리자 권한으로 격리
- 비밀번호·MFA·액세스 키 비밀값은 Terraform으로 생성하지 않아 state 유입 방지

### 다음 작업

- 참여 사용자와 관리자 명단 확인
- 각 사용자의 MFA 등록 확인
- 역할별 AWS 작업 권한을 현재 Terraform 관리 자원에 맞춰 코드화
- 별도 자격 증명으로 plan 성공과 apply 차단을 실제 검증

세부 설계는 [팀 Terraform 접근 권한 설계](team-terraform-access.md) 참조.

## 2026-09-19 — 지정 운영자용 Terraform 계획 역할 준비

### 운영 방식 결정

- 팀원 4명이 하나의 로그인 주체를 공유하던 방식 중단 결정
- 팀원별 IAM 사용자와 MFA를 사용해 작업 주체와 이력을 구분
- Terraform 실행은 초기 지정 운영자 한 명만 담당
- 일반 팀원에게 project state 접근 권한을 부여하지 않고 담당 서비스 역할만 제공

### 구현 범위

- 지정 운영자 한 명만 전환 가능한 `TerraformPlanRole` 정의
- 역할 신뢰 정책에 MFA 조건과 1시간 세션 제한 적용
- project state 본문은 읽기만 허용하고 state 쓰기·삭제 제외
- 동시 실행 제어에 필요한 project lock 객체만 생성·조회·삭제 허용
- 현재 관리 자원의 EC2·IAM·S3 설정 조회 권한만 포함
- 프로젝트 S3 객체 내용 조회와 인프라 변경 권한 제외
- 기존 사용자 권한 축소와 적용 역할은 계획 역할 검증 후 별도 변경으로 분리

### 구현 검증

- `terraform fmt -check -recursive` 통과
- Terraform 단위 테스트 2개와 Python 테스트 37개 통과
- 실제 원격 state 기준 저장 plan: **3 to add, 0 to change, 0 to destroy**
- IAM 역할·역할 인라인 정책·운영자 역할 전환 정책 외 다른 관리 자원 변경 없음 확인
- MFA 조건, state 쓰기 차단, S3 데이터 객체 조회 차단 자동 검사 통과
- AWS Access Analyzer 정책 검사 경고 0건

### 적용 후 확인할 항목

- 사용자 적용 결과: **3 added, 0 changed, 0 destroyed**
- 지정 운영자 MFA 등록과 1시간 역할 세션 전환 성공
- 적용 후 bootstrap plan에서 **No changes** 확인
- 역할 세션으로 project state와 현재 관리 자원 전체 조회 성공
- project state 읽기와 project lock 쓰기 허용 확인
- project state 쓰기, bootstrap state 읽기, 프로젝트 S3 데이터 객체 읽기, EC2 변경 요청 거부 확인
- 권한 검증 중 팀원이 진행 중인 임시 EC2 네트워크 변경 감지
- 해당 변경은 테스트 종료 전까지 유지하고 Terraform 영구 구성에는 반영하지 않기로 결정
- 드리프트를 포함한 변경 plan은 `prevent_destroy`에 의해 중단됐으며 실제 인프라 변경 없음

세부 운영 구조는 [팀 Terraform 접근 권한 설계](team-terraform-access.md) 참조.

## 2026-09-20 — 제한된 Terraform 적용 역할 준비

### 설계 선택

- 지정 운영자만 MFA가 확인된 1시간 세션으로 역할 전환
- 계획 역할의 조회 범위에 project state 쓰기와 검토된 자원 변경 권한 추가
- 실제 자원 ARN은 Git 제외 입력에서만 관리
- 일반적인 인플레이스 변경과 보안 그룹 규칙·IAM 정책 연결 변경 지원
- 새 자원 생성과 기존 주요 자원 삭제·교체는 별도 검토 대상으로 분리

### 방어 조건

- EC2 인스턴스와 종속 네트워크·볼륨 생성 및 삭제 명시적 거부
- IAM 역할·인스턴스 프로파일·관리형 정책 생성 및 삭제 명시적 거부
- S3 버킷 생성·삭제와 project state 삭제 명시적 거부
- bootstrap state 읽기·쓰기·삭제 명시적 거부
- `iam:PassRole`은 검토된 역할과 EC2 서비스로 제한
- 관리형 정책 연결 변경은 검토된 역할과 정책 ARN 조합으로 제한

### 사전 검증

- `terraform validate` 통과
- Terraform 단위 테스트 3개 통과
- 전체 Python 테스트 44개 통과
- 실제 원격 state 기준 저장 plan: **3 to add, 0 to change, 0 to destroy**
- AWS Access Analyzer 정책 검사 경고 0건
- 저장 plan 전용 검사에서 IAM 역할·역할 정책·운영자 전환 정책 세 개 외 mutation 없음 확인

팀원의 임시 인프라 테스트가 끝나기 전에는 프로젝트 apply를 실행하지 않음. 세부 절차는 [Terraform 적용 역할 사용 절차](use-terraform-apply-role.md) 참조.

## 2026-09-20 — 제한된 Terraform 적용 역할 검증 완료

### 적용 결과

- 사용자 적용 결과: **3 added, 0 changed, 0 destroyed**
- MFA 조건과 1시간 세션 제한이 적용된 역할 생성 확인
- 적용 후 bootstrap plan에서 **No changes** 확인
- MFA 역할 전환 후 실제 Apply 역할 세션 확인
- 임시 자격 증명으로 프로젝트 원격 state의 관리 자원 48개 조회 성공

### 권한 경계 검증

- project state 쓰기 허용 확인
- 등록된 EC2·보안 그룹·IAM 역할·모니터링 버킷의 인플레이스 변경 허용 확인
- project state 삭제와 bootstrap state 읽기·쓰기 명시적 거부 확인
- EC2 인스턴스 종료, 신규 인스턴스 실행, IAM 역할 생성, S3 버킷 삭제 명시적 거부 확인
- 등록되지 않은 EC2 인스턴스 제어 거부 확인
- 정책 시뮬레이션만 사용해 실제 운영 자원 변경 없음

Terraform이 MFA 입력을 직접 처리하지 못하는 제약을 실제 실행에서 확인해, AWS CLI가 발급한 임시 자격 증명을 현재 셸에 전달하는 절차를 사용 문서에 추가.

## 2026-09-20 — MFA 기반 Terraform 비상 관리자 역할 준비

### 배경

- 운영자 IAM 사용자가 상시 `AdministratorAccess`를 보유한 상태 확인
- PlanRole과 ApplyRole만으로는 bootstrap state, IAM 복구와 새 자원 생성 불가
- 상시 관리자 권한을 제거하기 전에 MFA 기반 비상 복구 경로 필요

### 설계

- 지정 운영자 한 명만 MFA로 전환 가능한 1시간 관리자 역할 추가
- AWS 관리형 `AdministratorAccess`를 역할 세션에만 연결
- bootstrap·project state 객체와 과거 버전, state 버킷 삭제 명시적 거부
- 세 Terraform 역할과 지정 운영자 IAM 사용자 삭제 명시적 거부
- 일반 plan·apply와 비상 관리자 사용 절차 분리

### 사전 검증

- `terraform validate` 통과
- Terraform 단위 테스트 4개 통과
- 전체 Python 테스트 50개 통과
- 저장 plan의 변경 대상을 네 IAM 자원으로 제한하는 전용 검사기 추가
- 실제 원격 state 기준 저장 plan: **4 to add, 0 to change, 0 to destroy**
- AWS Access Analyzer에서 신뢰 정책·삭제 방지 정책·역할 전환 정책 findings 0건
- 저장 plan 전용 검사에서 역할·관리자 정책 연결·삭제 방지 정책·운영자 역할 전환 정책 외 mutation 없음 확인

### 적용과 권한 전환 결과

- 사용자 적용 결과: **4 added, 0 changed, 0 destroyed**
- 적용 후 bootstrap plan에서 **No changes** 확인
- 지정 운영자의 MFA 비상 관리자 역할 전환 성공
- 실제 역할 세션으로 bootstrap state 버전, Terraform state와 IAM 조회 성공
- state 경로와 분리한 임시 객체의 생성·암호화·삭제와 전체 버전 정리 완료
- 정책 시뮬레이션에서 state 객체·과거 버전·버킷과 핵심 IAM 삭제 명시적 거부 확인
- 루트 계정 MFA 활성화와 루트 액세스 키 부재 확인
- 운영자를 상시 관리자 그룹에서 제거하고 역할 전환 정책 유지 확인
- 운영자 직접 권한으로 IAM 역할 생성, EC2 종료와 S3 버킷 삭제가 거부되는 상태 확인
- 비상 관리자 역할 세션으로 실행한 최종 bootstrap plan에서 **No changes** 확인

## 2026-09-20 — 팀 공통 관리자 역할 준비

### 운영 판단

- 팀원의 담당 영역이 고정되지 않고 필요에 따라 여러 AWS 자원을 함께 운영
- 초기에는 서비스별 세분화 역할보다 공통 관리자 역할을 사용하기로 결정
- 개인 IAM 사용자에 직접 관리자 정책을 연결하지 않고 MFA 임시 역할 세션 사용
- Terraform 운영자 계정과 세 Terraform 역할은 팀 공통 관리자 범위에서 제외

### 구현 범위

- Git 제외 입력에 등록된 세 팀원만 신뢰하는 `4EVR0TeamAdminRole` 추가
- MFA 조건을 유지하고 팀 운영 편의와 관리자 권한 노출 시간을 고려해 최대 2시간 세션 적용
- AWS 관리형 `AdministratorAccess`를 역할에 연결
- 본인 비밀번호·MFA 관리와 역할 전환만 제공하는 `4EVR0TeamUsers` 그룹 추가
- state·Terraform 역할·Terraform 운영자 변경 차단 정책 추가
- 팀원 변경 시 그룹 구성과 역할 신뢰 주체를 함께 갱신하도록 전용 plan 검사기 추가

### 사전 검증

- `terraform validate` 통과
- Terraform 단위 테스트 5개 통과
- 전체 Python 테스트 56개 통과
- 실제 원격 state 기준 저장 plan: **6 to add, 0 to change, 0 to destroy**
- 저장 plan 전용 검사에서 팀 그룹·그룹 정책·멤버십과 역할·관리자 정책 연결·보호 정책 외 mutation 없음 확인
- AWS Access Analyzer에서 역할 신뢰·보호·사용자 기본 정책 findings 0건

### 적용과 운영 인계 결과

- 사용자 적용 결과: **6 added, 0 changed, 0 destroyed**
- AWS에서 팀 공통 관리자 역할·그룹, 세 사용자 멤버십과 정책 연결 확인
- 신뢰 대상을 등록된 세 사용자로 제한하고 MFA 필수 조건과 최대 2시간 세션 확인
- 적용 후 비상 관리자 역할 세션의 bootstrap plan에서 **No changes** 확인
- 팀원별 최초 비밀번호 변경·MFA 등록·역할 전환 절차를 팀에 전달하고 운영 단계로 인계
- 개인별 등록 완료 여부는 저장소에서 별도로 검증하지 않으며, 인프라 구성 적용을 이번 작업의 완료 기준으로 기록

## 2026-09-20 — AWS 인벤토리 관리 경계 확정

### 조사 근거

- 기존 전 리전 읽기 전용 조사 결과와 현재 Terraform 편입 목록 대조
- 활성 17개 리전, API 응답 561건과 미해결 조회 오류 0건인 로컬 원본 사용
- 실제 자원 식별자·정책·접속 정보는 공개 문서에 포함하지 않음

### 최종 결정

- 핵심 서버·전용 네트워크·연결 IAM·상태 저장소·접근 역할은 Terraform 관리 대상으로 확정
- 기본 VPC·서브넷과 AWS 관리형 정책은 기존 자원을 조회해 참조
- Glue·Athena, 데이터 파이프라인 버킷, ECR·CI 역할, 홈서버 서비스 계정과 백업 산출물은 각 생성·운영 주체가 관리
- AWS 기본·서비스 연결 자원과 프로젝트 소유 근거가 없는 IAM 역할은 관리 대상에서 제외
- 팀 테스트용 EC2 보안 그룹 연결은 사용자가 유지하기로 한 운영 예외로 기록하고 영구 Terraform 구성에는 반영하지 않음

### 완료 판단

- 모든 발견 자원을 import하는 대신 변경 책임에 따라 관리·조회·외부 관리·제외로 분류
- 기존 마이그레이션 계획의 자원 목록과 소유 범위 확인 항목 완료 처리
- 알려진 운영 예외에서는 project plan에 네트워크 차이가 남을 수 있음을 문서화

## 2026-09-20 — Terraform PR 정적 검증 자동화

### 목적과 설계

- 로컬 형식·구성·회귀 검사를 pull request의 공통 품질 게이트로 전환
- AWS 자격 증명과 원격 state 없이 실행되는 정적 검증으로 범위 제한
- Terraform 1.16.1과 Python 3.13 사용
- 외부 GitHub Action을 검토한 릴리스의 전체 commit SHA로 고정
- 저장소 읽기 권한만 부여하고 동일 PR의 이전 실행을 자동 취소

### 검증 범위

- 전체 Terraform 구성의 `fmt -check -recursive`
- bootstrap과 project의 `init -backend=false -lockfile=readonly` 및 `validate`
- mock AWS provider를 사용하는 bootstrap `terraform test`
- Python plan 검사기 회귀 테스트
- 모든 PR·main push와 수동 실행 지원. 필수 검사 지정 시 문서 변경 PR에서도 상태가 누락되지 않도록 경로 필터 미사용

### 로컬 검증

- YAML 구문 검사 통과
- Terraform 형식 검사 통과
- Python 테스트 **56 passed**
- 깨끗한 임시 checkout에서 AWS provider 6.63.0 신규 설치 후 bootstrap·project 초기화 성공
- 두 Terraform 구성의 `validate` 통과
- bootstrap 테스트 **5 passed, 0 failed**
- 원격 backend 접근과 AWS API 호출 없이 검증 완료

### 운영 후속

- PR에서 GitHub Actions 실제 실행 결과 확인
- 최초 성공 후 branch protection의 필수 검사 등록 검토
- 실제 AWS plan은 향후 OIDC 읽기 전용 역할을 사용하는 별도 workflow로 분리
