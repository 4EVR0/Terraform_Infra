# GraphDB 연결 자원 Terraform 편입

## 목적

- 이미 편입된 GraphDB EC2에 연결된 전용 보안 그룹과 IAM 자원을 코드로 관리
- 실행 중인 서버와 권한을 변경하지 않고 현재 구성을 Terraform state에 등록
- 공용 자원과 GraphDB 전용 자원을 구분해 변경 영향 범위 제한

## 조사와 범위 결정

- EC2에 연결된 보안 그룹 중 GraphDB 전용 그룹만 이번 편입에 포함
- 여러 서버가 함께 사용하는 SSH 보안 그룹은 GraphDB 단독 자원이 아니므로 제외
- 전용 보안 그룹 본체와 기존 ingress·egress 규칙을 독립 자원으로 편입
- IAM 역할, 인스턴스 프로파일, 팀 관리형 정책과 현재 정책 연결을 함께 편입
- 실제 자원 ID, 규칙 값, 정책 ARN과 JSON 문서는 Git에서 제외된 로컬 변수 파일에 보관

## 구현

### 보안 그룹

- `aws_security_group.graphdb`에서 이름·설명·VPC·태그 관리
- ingress와 egress를 `aws_vpc_security_group_*_rule`로 분리해 규칙별 수명 주기 관리
- 검토한 그룹이 기존 EC2에 연결돼 있을 때만 계획을 허용하는 사전 조건 추가
- EC2의 전체 보안 그룹 집합에서 전용 그룹만 Terraform 자원 참조로 교체
- 공용 보안 그룹 연결은 기존 입력에 남겨 현재 연결 상태 유지

### IAM

- `aws_iam_role.graphdb`와 `aws_iam_instance_profile.graphdb`로 역할과 EC2 연결 구조 관리
- 팀이 만든 관리형 정책은 `aws_iam_policy.graphdb`로 정책 문서까지 관리
- AWS 관리형 정책을 포함한 기존 연결은 `aws_iam_role_policy_attachment.graphdb`로 관리
- 검토한 EC2 프로파일 이름과 편입 대상이 일치할 때만 계획 허용

### 안전장치

- 모든 편입 자원에 `prevent_destroy` 적용
- 정책 JSON 유효성, ARN 중복과 팀 관리형 정책의 역할 연결 여부 검증
- 저장한 plan의 정확한 import 주소·ID와 기존 관리 자원 무변경 여부를 검사기로 확인

## 검증 결과

- `terraform fmt -check -recursive` 통과
- `terraform validate` 통과
- Python 회귀 테스트 15개 통과
- 실제 AWS plan: **10 to import, 0 to add, 0 to change, 0 to destroy**
- 첫 계획에서 기존 규칙의 태그 없음과 빈 태그 맵 명시의 차이를 발견
- 빈 태그 맵을 제거한 뒤 기존 규칙을 수정하지 않는 계획으로 재검증

## 적용 순서

1. 작업 브랜치의 코드와 검증 결과 리뷰
2. PR 병합 후 `main`에서 backend 재초기화
3. 병합된 코드로 새 plan 생성 및 import 검사
4. 원격 state 로컬 백업과 무결성 확인
5. 사용자가 저장된 plan 적용
6. state 등록 확인과 후속 plan의 `No changes` 확인

## 적용 결과

- 병합된 `main`에서 원격 backend 재초기화 및 새 plan 생성
- 적용 직전 원격 state 백업과 무결성 확인
- 최종 계획: **10 to import, 0 to add, 0 to change, 0 to destroy**
- 사용자 apply 결과: **10 imported, 0 added, 0 changed, 0 destroyed**
- 대상 보안 그룹·규칙과 IAM 자원 10건의 원격 state 등록 확인
- 같은 변수 입력으로 실행한 후속 plan에서 **No changes** 확인

GraphDB EC2와 연결 자원의 실제 설정을 변경하지 않고 전용 보안 그룹과 IAM 구성을 Terraform 관리 대상으로 편입 완료.

## 한계와 후속 작업

- 이번 편입은 현재 설정을 그대로 코드화하며 접근 범위나 권한을 축소하지 않음
- 공용 SSH 보안 그룹은 여러 EC2에 영향을 주므로 별도 범위와 검증 절차 필요
- 네트워크 접근 최소화와 IAM 최소 권한화는 현행 동작과 사용 주체를 확인한 뒤 별도 변경으로 진행
- Terraform state 복구와 EC2 데이터 복구는 별개이므로 기존 백업 절차 유지 필요

## 참고

- [AWS provider 보안 그룹 문서](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/security_group)
- [AWS provider IAM 역할 문서](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role)
- [Terraform import 블록](https://developer.hashicorp.com/terraform/language/import)
