# GraphDB 공개 SSH 경로 단계적 제거

## 목적

- 프로젝트 EC2가 공유하는 SSH 보안 그룹을 GraphDB에서 분리
- GraphDB 관리 접속을 검증된 Tailscale 경로로 제한
- 여러 서버의 접속 경로를 한 번에 바꾸지 않고 서버별 검증 후 단계적으로 적용

## 대상 선정

- 프로젝트 EC2는 조사 시점에 모두 중지 상태이며 SSM 관리 대상으로 등록되지 않음
- Tailscale 등록이 확인된 서버는 GraphDB와 모니터링
- 현재 작업 장비의 공개키로 Tailscale SSH와 관리자 권한까지 검증된 서버는 GraphDB
- Airflow와 파이프라인은 대체 접속 경로를 먼저 구성해야 하므로 이번 변경에서 제외

## 사전 접속 검증

1. 중지된 GraphDB EC2 시작
2. AWS 시스템·인스턴스 상태 검사 정상 확인
3. Tailscale MagicDNS 주소와 기존 RSA 키로 새 SSH 연결 성공
4. 접속 계정과 비밀번호 없는 `sudo` 권한 확인
5. 검증 후 EC2를 기존 중지 상태로 복구

## 계획 중 발견한 교체 위험

최초 plan은 보안 그룹 변경이 아니라 동적 공인 IP 연결 상태 차이 때문에 EC2 교체를 제안. `prevent_destroy`가 이를 차단하여 실제 자원 변경은 발생하지 않음.

중지·시작에 따라 달라지는 동적 공인 IP 관측값을 `ignore_changes`에 추가하고 삭제 방지를 유지. 이후 plan에서 GraphDB의 보안 그룹 연결 하나만 인플레이스 변경으로 남는 것을 확인.

## 구현

- GraphDB EC2의 보안 그룹 집합에서 공용 SSH 그룹 참조 제거
- GraphDB 서비스 전용 보안 그룹 참조 유지
- 다른 EC2와 공용 보안 그룹·규칙은 변경하지 않음
- 저장된 plan에서 정확한 대상·제거 그룹·보존 그룹과 다른 관리 자원 무변경을 검사하는 스크립트 추가

## 검증 결과

- `terraform fmt -check -recursive` 통과
- `terraform validate` 통과
- Python 테스트 20개 통과
- Tailscale RSA SSH와 관리자 권한 검증 통과
- 검증 후 GraphDB를 기존 중지 상태로 복구
- 최종 plan: **0 to add, 1 to change, 0 to destroy**
- 계획 검사기: GraphDB에서 공용 그룹 하나만 제거, 전용 그룹 유지, 다른 관리 자원 변경 없음

## 적용 게이트

1. PR 병합 후 `main`에서 새 plan 생성
2. 적용 직전 원격 state 백업
3. GraphDB 시작 및 Tailscale SSH 재검증
4. 기존 SSH 세션을 유지한 상태로 저장된 plan 적용
5. 새 Tailscale SSH 세션 연결 확인
6. 후속 plan의 `No changes` 확인
7. GraphDB를 작업 전 상태로 복구

새 Tailscale SSH 연결이 실패하면 적용을 중단. 적용 후 문제가 생기면 AWS 관리 권한으로 기존 공용 그룹 연결을 복구하고 원인을 확인.

## 적용 결과

- 병합된 `main`에서 Tailscale RSA SSH와 관리자 권한 재검증
- 적용 직전 원격 state 백업과 전용 계획 검사 통과
- 사용자 apply 결과: **0 added, 1 changed, 0 destroyed**
- GraphDB에 서비스 전용 보안 그룹만 연결되고 공용 SSH 그룹이 제거된 상태 확인
- 공용 SSH 경로 차단과 Tailscale 새 SSH 세션 연결 성공 확인
- 비밀번호 없는 관리자 권한 재검증
- GraphDB를 기존 중지 상태로 복구
- 후속 plan에서 **No changes** 확인

따라서 AWS 공인 네트워크를 통한 GraphDB SSH 진입점을 제거하면서 Tailscale 관리 경로와 복구 권한 유지.

## 한계와 다음 작업

- 공용 SSH 그룹은 모니터링·Airflow·파이프라인에 계속 연결됨
- 모니터링은 팀원별 공개키 접속을 확인한 뒤 같은 방식으로 분리 가능
- Airflow와 파이프라인은 Tailscale 또는 SSM 관리 경로를 먼저 구성할 필요
- 동적 공인 IP 정책과 서버별 접속 경로를 장기적으로 명시해 재시작 후 노출 상태를 예측 가능하게 관리할 필요
