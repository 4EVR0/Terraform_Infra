# 모니터링 서버 SSM 관리 경로 추가

## 목적

- 모니터링 서버의 공개 SSH 의존성을 제거하기 전에 AWS Systems Manager 관리 경로 확보
- 기존 Tailscale 노드와 별개로 AWS 관리 권한을 이용한 복구 채널 준비
- 관리 채널 검증 전에는 기존 SSH 보안 그룹 연결 유지

## 사전 조사

- 모니터링 EC2는 Ubuntu 24.04 ARM64 이미지 사용
- Tailscale 노드는 등록돼 있지만 현재 작업 장비의 지속 가능한 SSH 키 접속은 미확인
- 연결된 IAM 역할에는 SSM 관리 정책이 없음
- Ubuntu AWS 이미지에는 SSM Agent가 기본 포함될 가능성이 있으나 정책 연결 전에는 온라인 관리 노드 여부를 검증할 수 없음

## 구현

- 모니터링 IAM 역할에 AWS 관리형 `AmazonSSMManagedInstanceCore` 정책 연결 추가
- 정책 자체는 AWS 관리형 자원으로 참조하고 역할과의 연결만 Terraform에서 관리
- 연결 자원에 `prevent_destroy` 적용
- 정책 연결 한 건 외 변경을 거부하고 역할·정책 ARN을 검사하는 plan 검사기 추가

## 계획 검증 결과

- `terraform fmt -check -recursive` 통과
- `terraform validate` 통과
- Python 테스트 25개 통과
- 실제 plan: **1 to add, 0 to change, 0 to destroy**
- 계획 검사기: 검토한 역할에 SSM 정책 연결 한 건만 생성, 다른 관리 자원 변경 없음

## 적용 및 실제 검증 결과

1. PR 병합 후 `main`에서 새 plan 생성 및 원격 state 백업 완료
2. 사용자 apply 결과: **1 added, 0 changed, 0 destroyed**
3. IAM 역할의 SSM 관리 정책 연결 확인
4. 모니터링 EC2를 잠시 시작해 SSM Agent `Online` 확인
5. SSM 원격 진단 명령 `Success`, 종료 코드 0, 실행 사용자 `root` 확인
6. 모니터링 EC2를 기존 중지 상태로 복구
7. 후속 plan의 **No changes** 확인

SSM을 독립적인 관리·복구 경로로 실제 사용할 수 있음을 확인. 다음 변경에서는 이 검증을 적용 전후 게이트로 사용.

## 트레이드오프와 후속 작업

- SSM 정책 연결은 모니터링 역할의 권한을 늘리는 변경
- 공개 SSH 제거 전에 대체 경로를 확보해 잠금 위험을 줄이는 이점이 더 큼
- 별도 PR에서 모니터링 EC2의 공용 SSH 그룹 연결 제거
- 팀 IAM 주체의 SSM 접근 권한과 감사 로그 보존 정책은 별도 검토 필요
