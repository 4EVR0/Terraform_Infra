# Airflow 보안 그룹과 규칙 편입

## 목적과 범위

- 편입된 Airflow EC2의 전용 보안 그룹 1개와 현재 규칙 4개 관리
- 여러 프로젝트 EC2가 함께 사용하는 공용 SSH 그룹은 참조만 유지
- 신규 포트 개방·기존 허용 범위 축소·EC2 시작·교체는 포함하지 않음
- 실제 보안 그룹·규칙 ID와 통신 소스는 Git 제외 로컬 tfvars에만 보관

이번 단계의 목표는 현재 통신 관계를 바꾸지 않고 관리 주소를 연결하는 것. 접근 범위 개선은 현재 상태 편입과 분리해 변경 영향과 복구 방법을 별도로 검토.

## 소유 범위 확인

- Airflow EC2에 연결된 보안 그룹 2개 조사
- 전용 그룹은 Airflow 네트워크 인터페이스 한 개에만 연결됨
- 공용 SSH 그룹은 프로젝트 EC2 네 대가 공유하므로 이번 소유 범위에서 제외
- 전용 그룹을 참조하는 제한된 내부 통신 규칙과 외부 접근 규칙을 현재 상태 그대로 보존

전용 그룹에서 외부 접근 범위가 넓은 규칙을 확인했으나 최초 import에서는 수정하지 않음. Airflow 운영 접속 경로와 인증 방식을 확인한 뒤 별도 보안 개선으로 제한 필요.

## 코드 구조와 보호 장치

- `aws_security_group.airflow`: 이름·설명·VPC·태그 관리
- `aws_vpc_security_group_ingress_rule.airflow`: 기존 인바운드 규칙별 관리
- `aws_vpc_security_group_egress_rule.airflow`: 기존 아웃바운드 규칙별 관리
- 그룹의 inline rule과 별도 rule 리소스를 혼용하지 않음
- Airflow EC2가 관리 그룹 리소스를 참조하도록 변경하되 최종 그룹 ID 집합 유지
- 검토한 전용 그룹이 기존 EC2 설정에 포함되는지 precondition으로 확인
- 그룹·규칙에 `prevent_destroy` 적용
- 각 규칙이 CIDR·prefix list·참조 그룹 중 정확히 한 소스만 갖도록 입력 검증

논리 규칙 key는 방향·프로토콜·포트·소스 유형을 기준으로 고정. 편입 이후 기존 key를 바꾸면 Terraform 관리 주소가 달라지므로 재명명하지 않음.

## 트러블슈팅

- 최초 plan: import 5건과 update 1건 발견
- 변경 후보는 전체 프로토콜 아웃바운드 규칙의 시작·종료 포트 표현
- AWS provider는 해당 포트를 `null`로 정규화하지만 조사 입력에는 `-1`이 포함됨
- 전체 프로토콜 규칙의 포트를 `null`로 맞추고 plan 재생성
- 수정 후 실제 정책 변경 없이 import 5건만 남는 결과 확인

차이를 `ignore_changes`로 숨기지 않고 provider의 현재 상태 표현에 맞춰 입력을 수정.

## 검증 결과

- Terraform fmt 및 validate 통과
- Python 회귀 테스트 14개 통과
- 실제 AWS plan: `5 to import, 0 to add, 0 to change, 0 to destroy`
- 예상 보안 그룹·규칙 주소와 실제 import ID 대응 검사 통과
- 기존 Airflow EC2와 모니터링 관리 자원 변경 없음 확인
- 사용자 실행으로 기존 보안 그룹 1개와 규칙 4개 import 완료
- 원격 state의 관리 주소 5개 등록 확인
- 적용 후 후속 plan에서 `No changes` 확인

## PR 머지 후 적용 순서

1. PR 검토와 main 머지
2. main 최신 코드와 Git 제외 입력 확인
3. 브랜치에서 만든 plan을 폐기하고 새 plan 생성
4. 예상 import 대응과 관리 자원 변경 없음 재검사
5. 원격 project state 비공개 백업
6. 검토한 저장 plan을 사용자 직접 적용
7. 후속 plan의 `No changes`와 state 등록 확인

```bash
.local/bin/terraform -chdir=environments/project plan \
  -out=../../.local/airflow-sg-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json \
  ../../.local/airflow-sg-after-merge.tfplan \
  > .local/airflow-sg-after-merge.json

python3 scripts/check_import_plan.py \
  .local/airflow-sg-after-merge.json \
  --expected-imports .local/airflow-security-group-expected-imports.json
```

예상 적용 결과: `5 imported, 0 added, 0 changed, 0 destroyed`.

## 한계와 후속 작업

- 보안 그룹 편입 plan은 실제 Airflow UI·Scheduler·DAG 통신 성공을 확인하지 않음
- 현재 외부 접근 범위의 적정성과 Airflow 인증 강도는 별도 검토 필요
- 개별 rule 방식은 Terraform에 등록하지 않은 외부 추가 규칙을 자동 제거하지 않으므로 주기적 목록 대조 필요
- 적용 완료 후 Airflow IAM 역할·인스턴스 프로파일·정책 연결 편입 준비

## 참고

- [AWS provider 보안 그룹 문서](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/security_group.html.markdown)
