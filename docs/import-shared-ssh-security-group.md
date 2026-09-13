# 프로젝트 공용 SSH 보안 그룹 편입

## 목적

- 프로젝트 EC2가 함께 사용하는 SSH 보안 그룹을 단일 Terraform 자원으로 관리
- 각 EC2 구성에 반복된 그룹 ID 입력을 명시적인 자원 참조로 전환
- 현행 연결과 규칙을 바꾸지 않고 관리 경계만 먼저 확정

## 소유 범위 판단

- 실제 네트워크 인터페이스 연결을 조회해 프로젝트 EC2들이 같은 그룹을 공유함을 확인
- 특정 서버 전용 구성에 넣지 않고 프로젝트 공용 자원으로 분리
- Terraform이 관리 중인 모니터링·Airflow·GraphDB EC2는 공용 그룹 자원을 직접 참조
- 편입을 보류한 파이프라인 EC2의 기존 연결은 유지

## 구현

- `aws_security_group.shared_ssh`에서 그룹 본체 관리
- ingress와 egress를 독립 규칙 자원으로 관리
- 검토한 공용 그룹이 관리 중인 세 EC2의 기존 입력에 모두 포함될 때만 계획 허용
- 세 EC2의 보안 그룹 집합에서 기존 공용 ID를 제거한 뒤 같은 자원의 Terraform 참조를 추가
- 모든 편입 자원에 `prevent_destroy` 적용
- 실제 그룹 ID와 규칙 값은 Git 제외 로컬 변수 파일로 분리

## 검증 결과

- `terraform fmt -check -recursive` 통과
- `terraform validate` 통과
- Python 회귀 테스트 15개 통과
- 실제 AWS plan: **3 to import, 0 to add, 0 to change, 0 to destroy**
- 계획 검사기에서 그룹 본체와 규칙 2건의 정확한 주소·ID 및 기존 관리 자원 무변경 확인

## 적용 순서

1. 작업 브랜치 리뷰 및 PR 병합
2. 병합된 `main`에서 backend 재초기화
3. 새 plan 생성과 import 집합 재검증
4. 적용 직전 원격 state 백업
5. 사용자 apply
6. 원격 state 등록과 후속 plan의 `No changes` 확인

## 트레이드오프와 후속 작업

- 현재 규칙을 그대로 편입하므로 import 자체는 접속 경로나 접근 범위를 개선하지 않음
- 편입과 접근 제한을 분리해 접속 장애 발생 시 원인을 구분할 수 있도록 구성
- 이후 각 서버의 Tailscale 접속과 팀원별 공개키 접근을 확인한 뒤 외부 SSH 접근 축소 검토
- 공용 규칙 변경은 연결된 모든 EC2에 영향을 주므로 별도 plan과 복구 경로 필요

## 참고

- [AWS provider 보안 그룹 문서](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group)
- [Terraform import 블록](https://developer.hashicorp.com/terraform/language/import)
