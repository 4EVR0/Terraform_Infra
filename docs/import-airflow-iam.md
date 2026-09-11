# Airflow IAM 자원 편입

## 목적과 범위

- Airflow EC2가 AWS 서비스에 접근할 때 사용하는 IAM 연결 관계 관리
- IAM 역할 1개, 인스턴스 프로파일 1개, AWS 관리형 정책 연결 5개 편입
- AWS 관리형 정책 자체는 AWS 소유이므로 역할과의 연결만 관리
- 기존 권한의 추가·축소, 역할 교체, EC2 시작은 포함하지 않음
- 실제 이름·ARN·신뢰 정책은 Git 제외 로컬 tfvars에 보관

## 소유 범위 확인

- 인스턴스 프로파일에 역할 1개만 연결됨을 확인
- 역할이 인스턴스 프로파일 1개에서만 사용됨을 확인
- 해당 프로파일을 사용하는 EC2가 Airflow 서버 1대뿐임을 확인
- 인라인 정책은 없으며 AWS 관리형 정책 연결 5개 확인

이 관계를 근거로 역할과 프로파일을 Airflow 전용 자원으로 판단. 공유 자원의 권한을 의도치 않게 관리하는 위험 없이 이번 편입 범위에 포함.

## 코드 구조와 보호 장치

- `aws_iam_role.airflow`: 역할 이름·경로·세션 시간·신뢰 정책 관리
- `aws_iam_instance_profile.airflow`: 프로파일과 역할 연결 관리
- `aws_iam_role_policy_attachment.airflow`: 기존 AWS 관리형 정책 연결별 관리
- 모든 편입 자원에 `prevent_destroy` 적용
- 신뢰 정책 JSON 유효성 검사와 관리형 정책 ARN 중복 차단
- Airflow EC2가 관리 프로파일 리소스를 참조하도록 전환
- 조사한 기존 프로파일과 편입 대상이 같은지 precondition으로 확인

관리형 정책 연결은 개별 리소스로 관리. Terraform에 아직 등록하지 않은 연결을 자동으로 제거하지 않아 최초 편입 과정에서 예상치 못한 권한 회수를 방지.

정책 연결의 논리 key는 역할 이름이나 정책 표시 순서와 분리한 고정 이름 사용. 기존 key를 변경하면 Terraform 관리 주소가 달라지므로 편입 후 재명명하지 않음.

## 검증 결과

- Terraform `fmt`·`validate` 통과
- Python 회귀 테스트 14개 통과
- 실제 AWS plan: `7 to import, 0 to add, 0 to change, 0 to destroy`
- 예상 IAM 주소·ID 7개의 정확한 대응 검사 통과
- 기존 Airflow EC2와 보안 그룹, 모니터링 관리 자원 변경 없음 확인

## PR 머지 후 적용 순서

1. main 최신 코드와 Git 제외 IAM 입력 확인
2. 머지된 main에서 새 plan 생성
3. 예상 import 대응과 기존 관리 자원 무변경 재검사
4. 원격 project state 비공개 백업
5. 검토한 저장 plan을 사용자가 적용
6. 후속 plan의 `No changes`와 state 등록 확인

```bash
.local/bin/terraform -chdir=environments/project plan \
  -out=../../.local/airflow-iam-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json \
  ../../.local/airflow-iam-after-merge.tfplan \
  > .local/airflow-iam-after-merge.json

python3 scripts/check_import_plan.py \
  .local/airflow-iam-after-merge.json \
  --expected-imports .local/airflow-iam-expected-imports.json
```

예상 적용 결과: `7 imported, 0 added, 0 changed, 0 destroyed`.

## 한계와 후속 작업

- 현재 권한이 실제 Airflow 작업에 필요한 최소 범위인지는 이번 편입에서 평가하지 않음
- 관리형 정책 일부는 넓은 권한을 제공하므로 CloudTrail과 실제 DAG 사용 기능을 근거로 별도 축소 필요
- plan은 Airflow 애플리케이션의 AWS API 호출 성공을 검증하지 않음
- 개별 연결 관리 방식이므로 Terraform 밖에서 추가된 정책 연결은 주기적인 목록 대조로 탐지 필요
- state와 plan에 IAM 설정이 저장되므로 접근 권한과 로컬 산출물 관리 필요

## 공식 근거

- [IAM 역할 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_role.html.markdown)
- [인스턴스 프로파일 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_instance_profile.html.markdown)
- [관리형 역할 정책 연결 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_role_policy_attachment.html.markdown)
