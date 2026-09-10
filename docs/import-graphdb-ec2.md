# GraphDB EC2 편입 준비와 보안 게이트

## 목적과 범위

- 실행 중인 GraphDB EC2 한 대를 `aws_instance.graphdb` 주소로 편입 준비
- 서버 재생성·중지·설정 변경 없이 현재 AWS 설정과 Terraform 코드 비교
- 보안 그룹과 IAM 인스턴스 프로파일은 이번 단계에서 기존 ID·이름으로 참조
- 루트 EBS는 EC2의 `root_block_device`에서 관리하고 별도 EBS 리소스로 중복 편입하지 않음
- 실제 AMI·네트워크·자원 ID는 Git 제외 로컬 tfvars에만 보관

GraphDB는 추천 서비스의 데이터 조회에 쓰이는 실행 중인 핵심 서버이므로, 남은 EC2 가운데 다음 대상으로 선정. 먼저 EC2 관리 관계를 안전하게 연결한 뒤 전용 보안 그룹과 IAM을 별도 작업으로 편입하는 순서.

## 구성 생성과 트러블슈팅

- `terraform plan -generate-config-out`으로 현재 AWS 설정 기반 초안 생성
- 자동 생성 코드의 `primary_network_interface`와 일반 네트워크 속성 충돌 제거
- `ipv6_address_count`와 `ipv6_addresses` 중 주소 목록만 유지
- provider 계산값과 현재 상태를 설명하지 않는 속성 제거
- `prevent_destroy`로 Terraform 삭제·교체 계획 방지
- 기존 `user_data`는 구성에 복사하지 않고 `ignore_changes` 적용

`prevent_destroy`는 Terraform 계획에 포함된 삭제·교체를 막는 장치. AWS 콘솔 삭제, 구성 자체 제거, 자격 정보 노출을 막는 기능은 아님.

## 발견된 보안 문제

실제 import plan을 검토하는 과정에서 기존 EC2 `user_data`에 사용자 계정 생성 정보와 자격 정보가 포함된 사실을 확인. Terraform import는 이 값을 plan과 state에 기록할 수 있으므로, AWS 변경이 0건이어도 현재 상태로는 apply하지 않음.

이를 놓치지 않도록 import 계획 검사기에 다음 조건 추가.

- EC2 import 대상이 plan의 관리 값에 존재하는지 확인
- `user_data`가 비어 있지 않으면 검사 실패
- 생성·수정·삭제가 없는 plan도 이 보안 조건을 통과해야 적용 가능

HashiCorp는 plan과 state에 민감한 자원 속성이 포함될 수 있으므로 접근 제어와 암호화를 적용하고 민감 자료로 취급하도록 안내. AWS는 실행 중인 EC2의 user data를 조회할 수 있지만 변경하려면 먼저 인스턴스를 중지해야 한다고 안내.

## 현재 검증 결과

- `terraform fmt -check -recursive`: 통과
- `terraform validate`: 통과
- Python 회귀 테스트 15개: 통과
- 실제 AWS 자원 변경 검사: `1 to import, 0 to add, 0 to change, 0 to destroy`
- EC2 user data 보안 검사: **차단**
- 실제 import 적용: 미수행

즉, Terraform 구성은 현재 EC2와 일치하지만 보안 선행 조건이 남아 있음. 저장된 plan에는 민감 정보가 있으므로 적용하거나 공유하지 않고 폐기.

## 적용 전 보안 조치

1. 초기화 스크립트에 포함되었거나 복사되었을 가능성이 있는 비밀번호·SSH 키 목록 확인
2. 서버에서 해당 자격 정보 교체 및 불필요한 키·계정 제거
3. GraphDB 중지 시간을 팀과 합의하고 서비스·데이터 백업 상태 확인
4. EC2 중지 후 기존 user data 삭제
5. EC2 재시작 후 SSH 접근, Neo4j 상태, 추천 서비스의 GraphDB 조회 확인
6. 새로운 import plan 생성 및 검사기 통과 확인
7. PR 머지 후 main에서 다시 plan·state 백업·사용자 apply 수행
8. 적용 후 `No changes`와 서비스 상태 재확인

user data 수정은 서버 내부 파일이나 이미 설정된 계정 정보를 자동으로 지우지 않음. user data 삭제와 실제 자격 정보 교체를 모두 수행해야 함.

## 보안 조치 후 검증 명령

```bash
# 민감한 plan 출력이 터미널 기록에 남지 않도록 로컬 파일로 제한
umask 077
.local/bin/terraform -chdir=environments/project plan \
  -out=../../.local/graphdb-import-after-remediation.tfplan \
  > .local/graphdb-import-after-remediation.txt
.local/bin/terraform -chdir=environments/project show -json \
  ../../.local/graphdb-import-after-remediation.tfplan \
  > .local/graphdb-import-after-remediation.json

python3 scripts/check_import_plan.py \
  .local/graphdb-import-after-remediation.json \
  --expected-imports .local/graphdb-expected-imports.json
```

예상 결과는 GraphDB EC2 import 1건, 관리 자원 변경 0건, 비어 있는 `user_data`. 보안 조치 전 저장한 plan은 사용하지 않음.

## 한계와 후속 범위

- import plan은 EC2 속성 일치만 확인하며 Neo4j 데이터 무결성과 애플리케이션 정상 동작을 보장하지 않음
- 공개 IP와 현재 보안 그룹 규칙의 적정성은 이번 무변경 편입에서 평가·수정하지 않음
- 연결된 전용 보안 그룹·규칙과 IAM 역할·정책은 EC2 적용 완료 후 별도 편입
- 자격 정보 교체와 user data 삭제에는 서비스 점검 시간과 팀 협의 필요

## 참고

- [AWS EC2 user data 수정과 삭제](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html)
- [Terraform의 민감 데이터와 state 보호](https://developer.hashicorp.com/terraform/language/manage-sensitive-data)
