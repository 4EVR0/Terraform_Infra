# 모니터링 보안 그룹과 규칙 편입

## 목적과 범위

- 이미 편입한 모니터링 EC2의 전용 보안 그룹 및 현재 규칙 관리
- 보안 그룹 1개, 인바운드 규칙 7개, 아웃바운드 규칙 1개 편입
- 공통 SSH 그룹과 다른 서버의 보안 그룹은 참조만 유지
- 신규 포트 개방·기존 허용 범위 축소·서버 기동·교체는 포함하지 않음
- 실제 AWS 설정·ID·규칙별 소스는 비공개 로컬 tfvars로 제공

## 의존 관계 조사

- 프로젝트 EC2의 그룹 연결을 비교해 모니터링 전용 후보 선택
- 계정/리전의 해당 그룹 연결 ENI 목록 조회로 모니터링 인스턴스 연결 확인
- 다른 보안 그룹에서 모니터링 그룹을 소스로 참조하는 규칙 확인
- 이 참조는 통신 의존 관계이며 다른 그룹까지 이번 Terraform 소유 범위에 포함한다는 의미는 아님
- 그룹 이름·ID와 기존 규칙을 유지하여 참조 관계 보존

## 코드 구조와 선택

- `aws_security_group.monitoring`: 이름·설명·VPC·태그 관리
- `aws_vpc_security_group_ingress_rule.monitoring`: 기존 ingress rule ID별 관리
- `aws_vpc_security_group_egress_rule.monitoring`: 기존 egress rule ID별 관리
- 그룹의 inline ingress/egress는 선언하지 않음. 별도 규칙 리소스와 혼용 방지
- EC2는 관리되는 그룹의 resource ID를 참조하도록 변경하되 최종 그룹 ID 집합은 유지
- 기존 EC2 설정에 대상 그룹이 포함되는지 precondition으로 확인
- 그룹·규칙에 prevent_destroy 적용. 의도적으로 규칙을 제거할 때는 보호 설정 변경도 함께 리뷰 필요
- 개별 규칙에 정확히 하나의 CIDR·prefix list·참조 그룹만 지정하도록 입력 검증

논리 rule key는 최초 입력 이후 고정. 규칙 추가 때 기존 키를 순서대로 재배정하면 관리 주소가 바뀌므로 재번호 부여 금지.

## 발견한 차이와 해결

- 첫 plan: 9 import, 8 update
- 차이는 기존 태그 없음과 명시적 빈 태그 맵의 표현 차이
- 기존 무태그 규칙은 null로 표현해 불필요한 업데이트 제거
- ignore_changes로 차이를 숨기지 않고 입력값 정합성 수정
- 최종 목표: **9 to import, 0 to add, 0 to change, 0 to destroy**

## 검증

- 실제 AWS plan에서 위 목표 결과 확인
- 단일 import 검사기를 정확한 주소→ID 묶음 검사로 확장, 기존 단일 검사 인터페이스 유지
- plan JSON에서 검토한 그룹/규칙 9개만 편입되고 EC2 등 다른 관리 자원의 변경이 없는지 확인
- Python 회귀 테스트 13개 통과
- PR #2 머지 후 사용자가 main에서 새 plan 생성·state 백업·apply 수행
- 사용자 실행 결과 보안 그룹과 규칙 편입 후 후속 plan에서 `No changes` 확인
- 원격 project state를 읽기 전용으로 조회해 보안 그룹 1개, 인바운드 규칙 7개, 아웃바운드 규칙 1개의 관리 주소 등록 확인

## 적용한 절차와 재현 방법

1. PR 검토·머지 후 main 최신 코드 준비
2. 실제 `monitoring_security_group` 입력과 기존 rule key/ID 검토
3. 검토한 기대 import 목록을 로컬 JSON으로 준비. plan 결과로 기대 목록을 역생성하지 않음
4. 새 plan 생성 및 목표 결과 확인
5. project state를 비공개 백업한 뒤 사용자 apply
6. 변경 없는 후속 plan, 규칙 수·소스·연결 관계 유지 확인

```bash
.local/bin/terraform -chdir=environments/project plan -out=../../.local/monitoring-sg-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json ../../.local/monitoring-sg-after-merge.tfplan > .local/monitoring-sg-after-merge.json
python3 scripts/check_import_plan.py .local/monitoring-sg-after-merge.json \
  --expected-imports .local/monitoring-sg-expected-imports.json
```

검토·백업 이후 사용자가 적용한 명령:

```bash
.local/bin/terraform -chdir=environments/project apply ../../.local/monitoring-sg-after-merge.tfplan
.local/bin/terraform -chdir=environments/project plan
```

저장 plan 적용은 확인 질문 없이 실행됨. 브랜치에서 만든 이전 plan은 머지 후 재사용하지 않음. 이번 편입에서는 머지된 main으로 새 plan을 생성해 적용함.

## 한계와 후속 작업

- 개별 rule 방식은 Terraform에 등록하지 않은 외부 추가 규칙을 자동 삭제하는 배타적 관리 방식이 아님. 주기적 AWS 규칙 목록 대조 필요
- 기존 공개 접근 범위가 적절한지는 별도 변경 PR에서 판단
- 연결 인터페이스 조사와 plan은 애플리케이션 통신 성공을 검증하지 않음
- 후속 `No changes`는 Terraform 관리 대상과 실제 AWS 설정의 일치를 뜻하며 Grafana·Prometheus·Loki의 정상 동작까지 증명하지 않음
- 다음 편입 후보는 모니터링 IAM 역할·프로파일·정책

## 공식 근거

- [AWS provider 보안 그룹 문서](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/security_group.html.markdown): 별도 ingress/egress rule 사용 권장 및 inline 규칙 혼용 금지
