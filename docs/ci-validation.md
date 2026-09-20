# Terraform PR 자동 검증

## 목적

- Terraform과 plan 검사기 변경을 main 병합 전에 검증
- 로컬에서 수행하던 형식·구성·회귀 검사를 팀 공통 품질 게이트로 전환
- AWS 자격 증명 없이 안전하게 실행되는 정적 검증 범위 유지

## 실행 조건

`.github/workflows/terraform-checks.yml`은 다음 경우 실행.

- 모든 pull request
- main push
- GitHub Actions 화면에서 수동 실행

동일한 pull request에 새 커밋이 올라오면 이전 실행을 취소하고 최신 커밋만 검증.

## 검증 항목

1. 전체 Terraform 파일의 `fmt -check`
2. bootstrap 구성의 backend 비활성 초기화와 `validate`
3. mock AWS provider를 사용하는 bootstrap `terraform test`
4. project 구성의 backend 비활성 초기화와 `validate`
5. Python plan 검사기 회귀 테스트

Terraform과 Python 버전을 명시하고 외부 GitHub Action은 전체 commit SHA로 고정.
두 Terraform lock 파일에는 개발 장비의 macOS ARM과 GitHub runner의 Linux AMD64 provider 체크섬을 함께 기록.

## 보안 경계

- 워크플로 권한은 저장소 내용 읽기로 제한
- AWS 액세스 키, 역할 전환 권한과 backend 설정 미사용
- `init -backend=false`로 원격 state 접근 차단
- `validate`와 mock provider 테스트만 수행하며 실제 plan·apply 미수행
- fork에서 생성된 pull request에도 AWS 자격 증명을 노출하지 않음

## 로컬 재현

저장소 루트에서 실행.

```bash
terraform fmt -check -recursive
terraform -chdir=bootstrap/state init -backend=false -input=false -lockfile=readonly
terraform -chdir=bootstrap/state validate
terraform -chdir=bootstrap/state test
terraform -chdir=environments/project init -backend=false -input=false -lockfile=readonly
terraform -chdir=environments/project validate
python3 -m unittest discover -s tests -v
```

기존 checkout이 원격 backend로 초기화되어 있다면 별도 임시 checkout에서 실행하는 편이 안전. `init -backend=false`는 새 CI checkout을 기준으로 설계.

## 운영 적용

- 최초 workflow 성공 확인 후 저장소 branch protection에서 `Format, validate, and test`를 필수 검사로 지정
- 검사 실패 시 로그에서 최초 실패 단계를 확인하고 같은 명령을 로컬에서 재현
- 실제 AWS plan 자동화는 OIDC 읽기 전용 역할을 사용하는 별도 workflow로 분리
