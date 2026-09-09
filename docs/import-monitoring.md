# 모니터링 EC2 첫 편입

## 목적과 범위

- 기존 모니터링 EC2 한 대를 `aws_instance.monitoring` 주소로 편입
- 서버 재생성·기동·설정 변경 없이 Terraform 관리 관계만 추가
- 연결된 보안 그룹·서브넷·IAM 프로파일은 기존 ID/이름 참조
- 루트 EBS 속성은 EC2의 root_block_device에서 관리. 별도 EBS 리소스로 중복 편입하지 않음
- 실제 값은 Git 제외 로컬 tfvars의 `monitoring_config`, 대상 ID는 `instance_ids["monitoring"]` 사용

## 구현과 선택

- import 블록 활성화 및 EC2 resource 정의
- 자동 생성 설정에서 상호 충돌하는 primary_network_interface와 일반 네트워크 옵션 정리
- IPv6 주소 목록과 주소 개수를 동시에 설정하지 않도록 주소 목록만 유지
- VPC 보안 그룹 ID 사용, 이름 기반 security_groups 중복 설정 제거
- 계산되는 tags_all 제거, 관리 입력은 tags로 유지
- 기존 user_data가 없는 조회 결과를 바탕으로 user_data 설정 미추가
- prevent_destroy로 Terraform의 삭제·교체 계획 억제. 콘솔 삭제나 구성 제거까지 방지하지는 않음
- 실제 설정값은 정적 로컬 입력으로 보관. 매번 live data source에서 복사해 변경 차이를 숨기지 않음

공개 코드만으로 실제 자원 값을 재구성할 수 없다는 한계가 있음. 다른 팀원은 검토된 로컬 입력을 비공개로 전달받아야 하며, 민감값이 없는 새 checkout에서는 값 없이 plan할 수 없음.

## 검증 결과

- Terraform fmt 및 validate 통과
- 실제 계정에 대해 `1 to import, 0 to add, 0 to change, 0 to destroy` 확인
- plan JSON에서 예상 ID·리소스 주소의 import 1개와 관리 자원의 변경 없음 확인
- Python 회귀 테스트 9개 통과(기존 인벤토리 4개 + import 계획 검사 5개)
- 실제 import 적용은 미수행. 조회·plan 시 backend 잠금 객체 생성/해제만 발생 가능

## PR 및 사용자 적용 순서

1. `feat/import-monitoring-ec2` 브랜치의 PR 검토
2. 팀 리뷰 후 main에 머지
3. 사용자가 main 최신 코드로 이동하고 실제 tfvars와 backend 설정 확인
4. 새로운 plan을 생성하고 목표 결과를 다시 확인
5. 검토한 새 plan만 사용자 직접 적용
6. 이후 plan의 변경 없음과 AWS 인스턴스 상태·볼륨 연결 유지 확인

브랜치에서 검증한 plan은 PR 근거이며, 머지 후 그대로 적용하지 않음.

```bash
# 저장소 루트, main 최신 코드 및 비공개 설정 준비 후 실행
.local/bin/terraform -chdir=environments/project init -backend-config=../../.local/project.tfbackend
.local/bin/terraform -chdir=environments/project plan -out=../../.local/monitoring-import-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json ../../.local/monitoring-import-after-merge.tfplan > .local/monitoring-import-after-merge.json

# EXPECTED_MONITORING_ID에는 로컬 입력의 검토된 monitoring ID 사용
python3 scripts/check_import_plan.py .local/monitoring-import-after-merge.json \
  --target aws_instance.monitoring --expected-id "$EXPECTED_MONITORING_ID"
```

검사기는 관리 대상 자원의 create/update/delete/replace, 예상과 다른 import, 불완전한 plan을 거절. AWS의 실제 동작과 모든 설정 의미를 검증하는 도구는 아니므로 사람이 plan을 함께 검토.

적용 직전 `terraform state pull`로 현재 project state의 비공개 백업 확보. 작업 중 다른 사람이 apply하지 않도록 조율.

```bash
# plan 검토와 백업 완료 이후에만 실행. 저장된 계획은 확인 질문 없이 적용됨.
.local/bin/terraform -chdir=environments/project apply ../../.local/monitoring-import-after-merge.tfplan
.local/bin/terraform -chdir=environments/project plan
```

예상 적용 결과: `1 imported, 0 added, 0 changed, 0 destroyed`. 적용 후 다른 결과가 나오면 다음 자원으로 확대하지 않고 원인 확인.

## 남은 범위

- 첫 import의 실제 apply 및 이후 변경 없음 검증
- 다른 AWS 자원 편입과 공유 IAM·네트워크의 소유 범위 확정
- 실제 Terraform state의 버전 복원 후 plan 검증

## 참고

- [Terraform import 구성 생성](https://developer.hashicorp.com/terraform/language/import/generating-configuration): 생성 코드는 검토·수정 대상이며 상충하는 속성이 생성될 수 있음
