# 모니터링 S3 자원 편입

## 목적과 범위

- Loki가 로그 데이터를 저장하는 기존 S3 버킷과 보호 설정 관리
- 버킷 본체, 서버 측 암호화, 공개 접근 차단, 객체 소유권 설정의 4개 자원 편입
- 버킷 이름과 실제 태그는 Git에서 제외된 로컬 tfvars에 보관
- 기존 객체 수정·삭제, 버킷 교체, 권한 변경, 버전 관리 활성화는 포함하지 않음

## 사용 관계와 위험

- 애플리케이션 설정에서 해당 버킷을 Loki 저장소로 참조하는 관계 확인
- 객체 목록의 key를 노출하지 않고 버킷이 비어 있지 않다는 사실 확인
- 버킷이 삭제되면 로그 데이터와 모니터링 조회 기능에 영향을 줄 수 있으므로 `force_destroy = false`와 `prevent_destroy` 적용
- 보호 설정 세 가지에도 `prevent_destroy`를 적용해 구성 제거 시 리뷰 없이 암호화·공개 접근 차단·소유권 제어가 사라지지 않도록 구성

## 코드 구조와 선택

- `aws_s3_bucket.monitoring`: 기존 버킷 본체와 태그 관리
- `aws_s3_bucket_server_side_encryption_configuration.monitoring`: 기존 서버 측 암호화 설정 관리
- `aws_s3_bucket_public_access_block.monitoring`: 공개 ACL·정책 차단 설정 관리
- `aws_s3_bucket_ownership_controls.monitoring`: 버킷 소유자 중심의 객체 소유권 설정 관리
- 정책·수명 주기·CORS·웹 호스팅·복제·객체 잠금 등 선택 설정은 최초 편입 범위에 포함하지 않음

버전 관리 활성화는 현재 자원을 그대로 연결하는 import가 아니라 실제 운영 동작 변경이므로 최초 편입에서 제외. 기존 자원의 소유권을 먼저 확보한 뒤 데이터 보존 비용과 삭제 복구 요구를 정해 별도 PR로 검토.

## 검증

- 실제 AWS 설정을 당일 읽기 전용으로 다시 조회
- 실제 plan: **4 to import, 0 to add, 0 to change, 0 to destroy**
- plan JSON에서 검토한 S3 주소·ID 4개만 import되는지 확인
- 기존 EC2·보안 그룹·규칙·IAM 자원 15개는 모두 `no-op` 확인
- Terraform `fmt`·`validate` 통과
- Python 회귀 테스트 14개 통과
- 실제 apply는 수행하지 않음

## 리뷰·머지 후 사용자 적용

1. PR 검토·머지 후 main 최신 코드 준비
2. 버킷 이름과 기대 import 목록을 로컬 파일에서 재검토
3. main에서 새 plan 생성
4. plan 검사기로 S3 4개만 import되고 기존 관리 자원에 변경이 없는지 확인
5. project state를 비공개로 백업한 뒤 사용자가 apply
6. 후속 plan의 `No changes`와 원격 state의 S3 관리 주소 확인

```bash
.local/bin/terraform -chdir=environments/project plan -out=../../.local/monitoring-s3-after-merge.tfplan
.local/bin/terraform -chdir=environments/project show -json ../../.local/monitoring-s3-after-merge.tfplan > .local/monitoring-s3-after-merge.json
python3 scripts/check_import_plan.py .local/monitoring-s3-after-merge.json \
  --expected-imports .local/monitoring-s3-expected-imports.json
```

검토·백업 이후 사용자가 적용할 명령:

```bash
.local/bin/terraform -chdir=environments/project apply ../../.local/monitoring-s3-after-merge.tfplan
.local/bin/terraform -chdir=environments/project plan
```

저장 plan 적용은 확인 질문 없이 실행됨. 브랜치에서 만든 plan은 머지 후 재사용하지 않음.

## 한계와 후속 작업

- import와 후속 plan은 Loki의 실제 S3 읽기·쓰기 성공을 검증하지 않음
- 서버 측 암호화 설정 편입은 기존 객체를 다시 암호화하거나 내용을 검사하는 작업이 아님
- 버전 관리와 수명 주기의 도입 여부는 객체 삭제 복구와 보존 비용 요구를 바탕으로 별도 설계 필요
- 개별 설정 리소스에 포함하지 않은 외부 설정은 주기적인 AWS 설정 목록 대조 필요
- S3 적용 완료 후 버전 관리·보존 정책 개선 또는 나머지 EC2 편입 진행

## 공식 근거

- [S3 버킷 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/s3_bucket.html.markdown)
- [서버 측 암호화 설정 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/s3_bucket_server_side_encryption_configuration.html.markdown)
- [공개 접근 차단 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/s3_bucket_public_access_block.html.markdown)
- [객체 소유권 설정 import](https://github.com/hashicorp/terraform-provider-aws/blob/v6.63.0/website/docs/r/s3_bucket_ownership_controls.html.markdown)
