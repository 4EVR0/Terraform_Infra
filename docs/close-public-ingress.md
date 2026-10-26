# 공개 인바운드 정리(베타 배포 전)

상태: 코드 준비. AWS 적용은 아래 절차대로 사용자가 MFA 적용 역할로 실행한다.

## 배경

2026-10-27 읽기 전용 점검에서 다음 포트가 `0.0.0.0/0`에 열려 있었다. 베타 체크리스트의 "DB/GPU/관리 포트의 인터넷 접근 차단" 조건을 충족하지 않는다.

| 포트 | 서버 | 보안 그룹 | 처리 |
| --- | --- | --- | --- |
| 22 | Airflow, 모니터링 | 팀 시험용 그룹(운영 예외) | 연결 해제 후 그룹 삭제 |
| 7474 | GraphDB | GraphDB 전용 | 규칙 삭제 |
| 8080 | Airflow | Airflow 전용 | 규칙 삭제 |
| 3000 | 모니터링 | 모니터링 전용 | 규칙 삭제 |
| 9090 | 모니터링 | 모니터링 전용 | 공개 규칙만 삭제(허용 IP 규칙 유지) |
| 8501 | 모니터링 | 모니터링 전용 | 규칙 삭제 |

- 22는 [알려진 운영 예외](aws-management-boundary.md#알려진-운영-예외)였다. 2026-10-27 사용자가 시험용 그룹 해제·삭제에 동의했다.
- 팀 접속은 Tailscale 경로를 쓴다. Tailscale 트래픽은 보안 그룹의 공개 규칙을 거치지 않으므로 공개 규칙을 지워도 팀 접속은 유지된다.
- VPC 내부·특정 IP·보안 그룹 참조 규칙(예: Loki 3100, Prometheus 수집)은 바꾸지 않는다.

## 코드 변경

- 전용 보안 그룹 3개의 **인바운드 규칙** 리소스에서 `prevent_destroy`를 뺐다. 규칙은 ignored tfvars에서 검토된 키를 지워 삭제한다.
- 보안 그룹 자체와 아웃바운드 규칙, EC2의 `prevent_destroy`는 그대로다.
- 삭제 보호 대신 `scripts/check_ingress_cleanup_plan.py`가 저장된 plan을 검사한다.
  - 허용: 검토한 인바운드 규칙 주소의 삭제(교체 금지)
  - 허용: 검토한 EC2에서 검토한 보안 그룹 하나만 떼는 in-place update(필수 서비스 그룹 유지, 다른 속성 변경 금지)
  - 그 밖의 managed 변경·import·교체·알 수 없는 값은 실패

## 적용 절차

1. **로컬 tfvars 준비**(git 제외 파일)
   - GraphDB 변수(`graphdb_config`, `graphdb_security_group`, `graphdb_iam`)가 있어야 project plan이 된다. 없는 checkout이면 검토된 원본을 비공개 경로에서 복구한다.
   - 모니터링 `associate_public_ip_address`를 실제 상태와 맞춘다. 현재 실제 인스턴스에 공인 IPv4가 있고, 기본 VPC에 NAT가 없어 Tailscale·SSM 아웃바운드에 필요하다. 값이 다르면 plan이 EC2 교체를 제안하고 `prevent_destroy`·검사기가 막는다.
   - 위 표의 공개 규칙(GraphDB 7474, Airflow 8080, 모니터링 3000·8501·9090의 `0.0.0.0/0`) 키를 각 `ingress` 맵에서 지운다. 지운 키를 기록해 둔다.
2. **계획 저장**: MFA 적용 역할로 `terraform -chdir=environments/project plan -out=ingress-cleanup.tfplan` 후 `terraform show -json ingress-cleanup.tfplan > ingress-cleanup.json`.
3. **검사**
   ```bash
   python3 scripts/check_ingress_cleanup_plan.py ingress-cleanup.json \
     --delete-rule 'aws_vpc_security_group_ingress_rule.graphdb["<KEY>"]' \
     --delete-rule 'aws_vpc_security_group_ingress_rule.airflow["<KEY>"]' \
     --delete-rule 'aws_vpc_security_group_ingress_rule.monitoring["<KEY>"]' \
     --detach 'aws_instance.airflow,<TEAM_TEST_SG_ID>,<AIRFLOW_SG_ID>' \
     --detach 'aws_instance.monitoring,<TEAM_TEST_SG_ID>,<MONITORING_SG_ID>'
   ```
   `--delete-rule`은 지운 키마다 하나씩 넣는다. `PASS`가 아니면 적용하지 않는다.
4. **적용**: 적용 직전 원격 state 백업 → 저장된 plan 적용 → 후속 plan `No changes` 확인.
5. **확인**: 외부 네트워크에서 위 포트 접속 차단, Tailscale로 Grafana·Airflow·Neo4j 접속, SSM 명령 채널 정상.
6. **시험용 그룹 삭제**: 연결이 모두 해제된 것을 확인한 뒤 팀 관리자 역할로 시험용 보안 그룹을 삭제한다(이 저장소가 관리하지 않는 자원).
7. 결과를 이 문서와 `aws-management-boundary.md`(운영 예외 종료)에 기록한다.

## 중단 조건

- 검사기 실패, EC2 교체 제안, 예상 밖 보안 그룹·IAM 변경
- Tailscale 접속 확인 실패 → 적용 전 상태로 되돌린다(삭제한 규칙은 ignored tfvars 키를 복원해 재생성)
