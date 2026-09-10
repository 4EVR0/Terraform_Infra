# Airflow EC2 편입

## 목적과 대상 선정

- 기존 Airflow EC2 한 대를 `aws_instance.airflow` 주소로 편입
- 서버 재생성·시작·설정 변경 없이 Terraform 관리 관계만 추가
- 실제 AMI·네트워크·자원 ID는 Git 제외 로컬 tfvars에 보관

남은 EC2 가운데 Airflow 서버는 프로젝트 문서에서 크롤링과 데이터 파이프라인을 조율하는 메인 서버로 확인. 파이프라인 테스트 EC2보다 역할과 장기 관리 가치가 명확하므로 먼저 편입 대상으로 선정.

현재 인스턴스는 중지 상태이며 import는 이 상태를 바꾸지 않음. Terraform 편입과 Airflow 서비스 재가동은 별도 작업.

## 관리 범위

- EC2 인스턴스 속성과 루트 EBS 설정
- 연결된 보안 그룹은 기존 ID 참조
- IAM 인스턴스 프로파일은 기존 이름 참조
- 루트 EBS는 `root_block_device`에서만 관리하고 별도 EBS 리소스로 중복 편입하지 않음
- Terraform의 삭제·교체 계획을 막기 위한 `prevent_destroy` 적용

보안 그룹·규칙과 IAM 역할·정책 연결은 현재 통신과 권한을 유지한 채 후속 PR에서 별도 편입. 공유 자원 경계를 확인하기 전에 EC2와 함께 일괄 관리하지 않음.

## 구성 생성과 트러블슈팅

- import 초안 생성 전에 EC2 user data 존재 여부를 내용 출력 없이 확인
- 확인 결과: user data 비어 있음
- `terraform plan -generate-config-out`으로 실제 AWS 설정 기반 초안 생성
- 자동 생성된 `primary_network_interface`와 일반 네트워크 속성 충돌 제거
- `ipv6_address_count`와 `ipv6_addresses` 중 주소 목록만 유지
- 계산값을 제거하고 실제 설정을 `airflow_config` 로컬 입력으로 분리

자동 생성 코드의 충돌은 AWS 설정 차이가 아니라 provider가 읽은 계산 속성을 동시에 구성으로 표현하면서 발생. 상충 속성을 제거한 뒤 probe plan으로 실제 변경이 없는지 다시 확인.

## 검증 결과

- `terraform fmt -check -recursive`: 통과
- `terraform validate`: 통과
- Python 회귀 테스트 14개: 통과
- 실제 AWS plan: `1 to import, 0 to add, 0 to change, 0 to destroy`
- plan JSON의 예상 주소·ID 일치와 기존 관리 자원 변경 없음 검사: 통과
- Airflow EC2 user data 비어 있음 검사: 통과
- 실제 import 적용 및 후속 `No changes` 확인: 완료
- 원격 state의 `aws_instance.airflow` 등록 확인: 완료

plan은 EC2 속성 일치를 확인하지만 서버 내부의 Airflow, PostgreSQL, DAG 상태나 데이터 무결성을 확인하지 않음.

## 적용 결과

- PR #9 머지 후 main에서 새 plan 생성
- 적용 직전 원격 state 비공개 백업 및 JSON 유효성 확인
- 사용자 실행으로 기존 Airflow EC2를 `aws_instance.airflow` 주소에 연결
- 사용자 후속 plan에서 `No changes` 확인
- 원격 state 목록에서 Airflow EC2 등록을 읽기 전용으로 확인
- 인스턴스는 기존 중지 상태 유지

이번 적용은 기존 EC2를 생성·수정·시작하지 않고 Terraform state와 관리 주소를 연결한 작업. Airflow 애플리케이션의 실행 상태를 확인한 결과는 아님.

## PR 머지 후 적용 절차

1. 작업 브랜치의 PR 검토 및 main 머지
2. main 최신 코드와 Git 제외 로컬 입력 확인
3. 이전 plan을 폐기하고 새 plan 생성
4. plan JSON 검사와 원격 state 백업
5. 검토한 새 plan을 사용자 직접 적용
6. 후속 plan의 `No changes`와 원격 state 등록 확인

```bash
git switch main
git pull --ff-only

umask 077
.local/bin/terraform -chdir=environments/project plan \
  -out=../../.local/airflow-import-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json \
  ../../.local/airflow-import-after-merge.tfplan \
  > .local/airflow-import-after-merge.json

python3 scripts/check_import_plan.py \
  .local/airflow-import-after-merge.json \
  --expected-imports .local/airflow-expected-imports.json

.local/bin/terraform -chdir=environments/project state pull \
  > .local/project-state-before-airflow-import.json
.local/bin/terraform -chdir=environments/project apply \
  ../../.local/airflow-import-after-merge.tfplan
.local/bin/terraform -chdir=environments/project plan
```

예상 적용 결과: `1 imported, 0 added, 0 changed, 0 destroyed`. 적용 전후 인스턴스는 계속 중지 상태여야 하며, 다른 결과가 나오면 다음 자원으로 확대하지 않고 원인 확인.

## 한계와 후속 작업

- 중지 상태이므로 Airflow UI·Scheduler·DAG 실제 동작은 이번 편입에서 검증하지 않음
- 연결 보안 그룹의 외부 노출 적정성과 IAM 최소 권한 여부는 평가하지 않음
- EC2 편입 완료 후 Airflow 전용 보안 그룹·규칙과 IAM 역할·정책 연결 조사
- 서비스 재가동이 필요하면 데이터·환경 변수·컨테이너 상태를 확인하는 별도 운영 절차 수행

## 참고

- [Terraform import 구성 생성](https://developer.hashicorp.com/terraform/language/import/generating-configuration)
