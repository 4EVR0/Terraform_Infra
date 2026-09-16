# Airflow 공개 SSH 경로 단계적 제거

## 목적

- Airflow EC2에서 프로젝트 공용 SSH 보안 그룹 제거
- 공개 SSH 대신 AWS Systems Manager 관리 채널 사용
- Airflow 전용 서비스 통신과 다른 서버의 SSH 연결은 그대로 유지

## 대체 관리 경로 검증

- Airflow IAM 역할에 Systems Manager 관리 정책이 연결된 상태 확인
- 중지된 Airflow를 시작한 뒤 SSM Agent가 `Online`으로 등록되는지 확인
- SSM Run Command로 root 권한의 진단 명령 실행 성공
- Ubuntu의 SSM Agent가 Snap 서비스 단위로 실행 중임을 확인
- 검증 후 Airflow를 기존 중지 상태로 복구

첫 진단은 일반 패키지용 서비스 이름을 조회해 실패했지만, 명령 자체가 서버에서 root로 실행되고 응답한 사실을 확인. Snap 설치에 맞는 서비스 단위로 다시 실행해 성공 결과 확보.

## 구현

- Airflow EC2의 보안 그룹 집합에서 공용 SSH 그룹 참조 제거
- Airflow 전용 보안 그룹 참조 유지
- 공용 그룹 본체·규칙과 다른 EC2 연결은 변경하지 않음
- 기존 보안 그룹 분리 계획 검사기로 정확한 대상·제거 그룹·보존 그룹과 다른 자원 무변경 검증

## 검증 결과

- `terraform fmt -check -recursive` 통과
- `terraform validate` 통과
- Python 테스트 20개 통과
- SSM Agent 온라인과 root 명령 채널 검증 통과
- 최종 plan: **0 to add, 1 to change, 0 to destroy**
- 계획 검사기: Airflow에서 공용 그룹 하나만 제거, 전용 그룹 유지, 다른 관리 자원 변경 없음

## 적용 게이트

1. PR 병합 후 `main`에서 새 plan 생성
2. 적용 직전 원격 state 백업
3. Airflow 시작 및 SSM Agent 온라인 확인
4. SSM root 진단 명령 성공 확인
5. 저장된 plan 적용
6. 공용 SSH 경로 차단과 SSM 명령 재실행 확인
7. 후속 plan의 `No changes` 확인
8. Airflow를 기존 중지 상태로 복구

SSM 연결이 실패하면 적용을 중단. 적용 후 문제가 생기면 AWS 관리 권한으로 기존 공용 그룹을 다시 연결하고 원인을 확인.

## 한계와 다음 작업

- 로컬 Session Manager 플러그인이 없어 이번 검증은 SSM Run Command를 사용
- 대화형 세션은 AWS 콘솔 또는 플러그인이 설치된 관리 장비에서 별도 확인 필요
- 공용 SSH 그룹은 모니터링과 파이프라인에 계속 연결됨
- 모니터링은 Tailscale 계정별 공개키를, 파이프라인은 Tailscale 또는 SSM 경로를 먼저 준비해야 분리 가능
