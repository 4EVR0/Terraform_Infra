# 모니터링 IAM 자원 편입

## 목적과 범위

- 모니터링 EC2가 AWS 서비스에 접근할 때 사용하는 IAM 연결 관계 관리
- 역할 1개, 인스턴스 프로파일 1개, 인라인 정책 2개, AWS 관리형 정책 연결 1개 편입
- AWS 관리형 정책 자체는 AWS가 소유하므로 생성하지 않고 역할과의 연결만 관리
- 기존 권한 추가·축소, 역할 교체, EC2 재시작은 포함하지 않음
- 실제 이름·ARN·신뢰 정책·권한 정책 본문은 Git에서 제외된 로컬 tfvars에 보관

## 자원 관계

1. EC2가 인스턴스 프로파일 사용
2. 인스턴스 프로파일이 IAM 역할 연결
3. 역할의 신뢰 정책이 EC2의 역할 사용 허용
4. 인라인 정책과 AWS 관리형 정책 연결이 역할의 AWS 접근 권한 구성

EC2의 `iam_instance_profile`을 기존 문자열 입력에서 `aws_iam_instance_profile.monitoring.name` 참조로 전환. 사전 조건으로 조사한 기존 프로파일 이름과 편입 대상이 같은지 확인하여 잘못된 연결 방지.

## 코드 구조와 선택

- `aws_iam_role.monitoring`: 역할 이름·경로·설명·세션 시간·신뢰 정책 관리
- `aws_iam_instance_profile.monitoring`: 프로파일과 역할 연결 관리
- `aws_iam_role_policy.monitoring`: 기존 인라인 정책을 안정적인 논리 키별 관리
- `aws_iam_role_policy_attachment.monitoring`: 기존 AWS 관리형 정책 연결 관리
- 네 자원 유형에 `prevent_destroy` 적용
- 신뢰·권한 정책은 JSON 문자열 유효성 검사 적용
- 인라인 정책 이름과 관리형 정책 ARN의 중복 입력 차단

관리형 정책 연결을 개별 리소스로 관리하므로 다른 연결을 자동으로 제거하는 배타적 방식은 아님. 기존 권한을 변경 없이 편입하는 이번 단계에서는 의도하지 않은 권한 회수를 피하기 위해 이 방식을 선택.

논리 policy key는 최초 입력 이후 고정. 이름 정렬이나 정책 추가를 이유로 기존 키를 재배정하면 Terraform 관리 주소가 바뀌므로 재번호 부여 금지.

## 계획 검사기 보완

- 최초 plan 검사에서 역할과 인스턴스 프로파일의 import 문자열이 같아 중복 ID 오류 발생
- 서로 다른 AWS 자원 유형은 같은 이름을 합법적으로 사용할 수 있음을 반영
- 동일한 Terraform 자원 유형 안에서만 import ID 중복을 금지하도록 검사기 수정
- 서로 다른 자원 유형의 동일 ID 허용과 같은 유형의 중복 차단 회귀 검사 추가

## 검증

- 실제 AWS 설정을 당일 읽기 전용으로 다시 조회해 로컬 입력 생성
- 실제 plan: **5 to import, 0 to add, 0 to change, 0 to destroy**
- plan JSON에서 검토한 IAM 주소·ID 5개만 import되는지 확인
- 기존 EC2·보안 그룹·규칙은 모두 `no-op` 확인
- Terraform `fmt`·`validate` 통과
- Python 회귀 테스트 14개 통과
- 실제 apply는 수행하지 않음

## 리뷰·머지 후 사용자 적용

1. PR 검토·머지 후 main 최신 코드 준비
2. 실제 정책 문서와 import 기대 목록을 로컬 파일에서 재검토
3. main에서 새 plan 생성
4. plan 검사기로 IAM 5개만 import되고 기존 관리 자원에 변경이 없는지 확인
5. project state를 비공개로 백업한 뒤 사용자가 apply
6. 후속 plan의 `No changes`와 원격 state의 IAM 관리 주소 확인

```bash
.local/bin/terraform -chdir=environments/project plan -out=../../.local/monitoring-iam-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json ../../.local/monitoring-iam-after-merge.tfplan > .local/monitoring-iam-after-merge.json
python3 scripts/check_import_plan.py .local/monitoring-iam-after-merge.json \
  --expected-imports .local/monitoring-iam-expected-imports.json
```

검토·백업 이후 사용자가 적용할 명령:

```bash
.local/bin/terraform -chdir=environments/project apply ../../.local/monitoring-iam-after-merge.tfplan
.local/bin/terraform -chdir=environments/project plan
```

저장 plan 적용은 확인 질문 없이 실행됨. 브랜치에서 만든 plan은 머지 후 재사용하지 않음.

## 한계와 후속 작업

- 기존 권한 범위의 적정성은 이번 편입에서 평가하거나 변경하지 않음. 최소 권한 조정은 실제 접근 로그와 사용 기능을 확인한 별도 PR로 진행
- Terraform state와 plan에는 정책 본문이 저장되므로 로컬 산출물과 원격 state 접근 권한 관리 필요
- import plan은 EC2 애플리케이션이 AWS API를 정상 호출하는지 검증하지 않음
- 다음 편입 후보는 모니터링 관련 S3 자원

## 공식 근거

- [IAM 역할 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_role.html.markdown)
- [인스턴스 프로파일 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_instance_profile.html.markdown)
- [인라인 역할 정책 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_role_policy.html.markdown)
- [관리형 역할 정책 연결 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/iam_role_policy_attachment.html.markdown)
