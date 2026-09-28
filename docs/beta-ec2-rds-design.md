# 초대형 베타 EC2 + RDS 설계

상태: 구현 전 검토안. 이 문서의 병합은 AWS 자원 생성이나 IAM 권한 확대 승인이 아니다.

## 결정과 범위

- 서울 리전, 앱 EC2 `t4g.medium`(ARM64, 2 vCPU/4 GiB), RDS PostgreSQL `db.t4g.small`(2 vCPU/2 GiB)을 기준으로 설계한다.
- 앱 EC2에는 기존 FastAPI/웹 UI, Caddy, 운영 Redis를 Docker Compose로 실행한다.
- 그래프·모니터링 서버는 기존 자원을 재사용하되 현재 용량과 연결 가능 여부를 읽기 전용으로 재확인한다.
- GPU는 외부 vLLM/Tailscale 경로를 유지한다. GPU 운영 시간과 웹/DB 가동 시간을 분리한다.
- 이번 변경은 문서만 포함한다. 실제 계정 조회, plan/apply, 비밀 생성·조회, 서버 생성은 수행하지 않았다.

## 소유권과 상태

| 대상 | 제안 소유자 | 주의 |
|---|---|---|
| 앱 EC2/EBS/EIP, 전용 SG, 앱 인스턴스 역할 | Terraform project 상태 | 기존 서버와 구분되는 `beta_*` 주소/이름 사용 |
| RDS, DB subnet group, DB SG, parameter group | Terraform project 상태 | DB 삭제 보호 및 복구 절차 적용 |
| 기존 VPC/서브넷/라우트 | 읽기 전용 참조 | 공유 라우트나 기본 SG를 변경하지 않음 |
| 새 DB 전용 서브넷이 필요한 경우 | 별도 검토 후 Terraform project 상태 | CIDR·AZ·라우트 확인 전 생성 코드를 확정하지 않음 |
| ECR/이미지, GitHub OIDC/CI 역할 | 기존 앱 배포 영역 | 기존 관리 경계 유지, 이중 관리 금지 |
| Docker/Caddy/DB 연결·SQL 마이그레이션 | 앱 저장소 | 인프라 apply와 앱 배포를 분리 |
| 관측 수집·대시보드 | 모니터링 저장소 | 공개 `/metrics`를 열지 않음 |

초기에는 기존 project 상태를 유지하는 안으로 설계한다. 별도 상태가 필요하면 backend key와 접근 정책부터 별도 검토한다.
기존 plan 검사기는 신규 create를 허용한다고 가정하지 않는다. 새 자원 주소의 명시적 allowlist와 거부 회귀 테스트가 필요하다.

## 네트워크

1. 기존 VPC의 DNS, 공개 앱 서브넷의 인터넷 게이트웨이 경로, 사용 가능한 IP를 확인한다.
2. RDS subnet group은 동일 VPC의 서로 다른 AZ에 있는 최소 두 서브넷을 사용한다. Single-AZ DB여도 이 조건은 필요하다.
3. DB 전용 private 서브넷을 우선한다. 기존 기본 서브넷을 private로 바꾸지 않는다. 적합한 서브넷이 없으면 신규 서브넷 설계를 승인받는다.
4. RDS는 `publicly_accessible=false`, 앱 SG에서 TCP 5432만 허용한다. DB에 공인 IP를 부여하지 않는다.
5. 앱과 DB의 AZ를 가능한 한 맞추되 선택한 AZ에서 해당 DB 클래스/버전 지원을 확인한다.

| 경로 | 허용 범위 |
|---|---|
| 인터넷 → Caddy | TCP 80/443만 공개. 80은 HTTPS 전환/인증서 발급 용도 |
| 관리자 → 앱 | SSM 우선. 공개 SSH는 열지 않음 |
| 앱 → PostgreSQL | 앱 SG → DB SG, TCP 5432, TLS 인증서/호스트 검증 |
| 앱 → Neo4j | VPC 비공개 주소와 기존 GraphDB SG의 명시적 앱 SG 규칙 검토 |
| 앱 → GPU | Tailscale ACL과 컨테이너 DNS/라우팅 검증. GPU 포트를 공개하지 않음 |
| 앱 → Redis | Compose 내부 네트워크만 사용, 호스트 6379 공개 금지 |
| 관측 경로 | 기존 모니터링과 비공개 연결. 방향·수집 방식은 모니터링 PR에서 확정 |

앱 outbound는 OS/이미지/SSM/Tailscale 연결 요구를 조사해 별도 명시한다. 임의 IP 고정이나 제한이 이미 검증됐다고 가정하지 않는다.
앱은 공개 서브넷의 EIP를 사용하므로 기본안에 NAT Gateway나 ALB를 넣지 않는다.
RDS 관리 기능 때문에 고객 NAT Gateway가 필요하다고 가정하지 않는다.

## 앱 EC2

- ARM64 AMI ID를 검토·고정한다. 배포마다 최신 AMI를 자동 선택해 교체하지 않는다.
- 암호화 gp3 30GiB, IMDSv2 필수, 컨테이너의 인스턴스 메타데이터 접근은 기본 불허 방향으로 설계한다.
- SSM용 호스트 권한과 ECR pull/필요한 앱 secret 조회 권한만 분리 부여한다. Terraform 적용 권한을 앱 역할에 주지 않는다.
- root 디스크에는 애플리케이션의 유일한 영구 원본을 두지 않는다. Redis/Caddy 볼륨의 손실·복원 정책은 별도로 검증한다.
- T 계열 CPU 크레딧 모드와 경보를 명시한다. 성능/초과 비용을 부하 시험에서 확인한다.
- ARM64 릴리스 이미지 digest를 검증한 뒤 배포한다. 현재 AMD64 중심 CI와 별개로 ARM64 릴리스 검증을 추가해야 한다.
- user data/state에 DB 비밀번호·Tailscale 키를 넣지 않는다. 도구 설치와 비밀 주입을 분리한다.

## RDS 보호 설정

- PostgreSQL Single-AZ, gp3 20GiB. 엔진은 앱과 호환되는 표준 지원 버전을 명시하고 서울 클래스 지원을 확인한다.
- Multi-AZ 자동 장애 전환을 제공하지 않는다는 점을 운영 안내에 반영한다.
- 저장 암호화, 삭제 방지, Terraform `prevent_destroy`, 삭제 시 최종 snapshot을 기본 보호로 설계한다.
- 자동 백업 7일, 백업/유지보수 시간은 초대 운영 시간과 겹치지 않게 UTC로 명시한다.
- 저장소 자동 확장은 비용 상한과 함께 결정한다. 자동 축소는 기대하지 않는다. 여유 공간 경보를 먼저 구성한다.
- CPU·메모리·연결 수·저장 공간·CPU 크레딧을 관측하고 복구 시험을 출시 조건으로 둔다.
- master 비밀번호는 RDS 관리형 Secrets Manager 연동을 우선 검토한다. Terraform 평문 password 입력/출력은 금지한다.
- 앱은 master 계정이 아닌 최소 권한 DB 계정을 사용한다. 마이그레이션 계정과 런타임 계정을 분리한다.
- master secret과 앱 계정 secret은 다르다. 앱 비밀번호 교체 시 연결 풀/컨테이너 갱신을 포함한 절차를 구현한다.
- asyncpg 연결은 RDS CA 및 호스트 검증을 수행하도록 앱에서 테스트한다. 연결 문자열을 로그에 남기지 않는다.
- 복원은 새 DB로 수행하고 검증 후 endpoint/secret을 전환한다. 앱 rollback을 위해 DB를 파괴적으로 되돌리지 않는다.

## 생성 권한: 현재 적용 역할로 진행하지 않음

현재 적용 역할은 기존 EC2의 제한된 변경을 위한 역할이며 신규 EC2/SG/IAM 생성 등을 명시적으로 차단한다.
일반 Allow 추가만으로 명시적 Deny를 우회할 수 없고, RDS 생성 권한도 현재 범위에 포함된다고 가정하면 안 된다.

후속 IAM PR에서 신규 베타 프로비저닝용 MFA 역할을 별도로 검토한다.
서울 리전·프로젝트 태그·허용 AMI/인스턴스 유형·PassRole 대상·project state 경계를 가능한 조건으로 제한한다.
서비스별 tag 조건 지원과 생성 시 필요한 부수 API를 확인하고 거부 테스트를 작성한다.
실제 적용은 권한 변경 승인, 새 plan 검토, 사용자 생성 승인 후 수행한다. 상시 AdministratorAccess 복원은 해결책으로 삼지 않는다.

## 단계별 구현과 승인 기준

1. 읽기 전용 점검: 예상 계정 확인 후 VPC/서브넷/AZ/라우트/GraphDB SG/SSM 경로/DB 클래스·버전 가용성 조사. 결과는 비공개 로컬 기록.
2. 자원 코드 PR: 실제 ID는 ignored tfvars, 기본 비활성 옵션, 생성 전제조건, 보호 설정, mock provider 회귀 테스트 작성. 비활성 상태는 기존 자원 변경 0건을 요구한다.
3. IAM/plan 검사 PR: 새 자원 허용 범위를 제한하고 기존 서버 삭제·교체가 계속 거부되는지 검증한다.
4. AWS plan 검토: 의도한 신규 자원과 승인된 연결 규칙만 허용. 기존 팀 테스트 네트워크 예외와 드리프트를 해결하고 비용·백업·복구 조건 확인.
5. 사용자 승인 후 저장 plan 적용. 후속 plan 차이, SSM, 비공개 DB/TLS, 백업 복구, 앱 `/ready` 확인.
6. 앱 배포 PR: 이미지 digest/비밀 주입/도메인 HTTPS/동의·피드백/관측/운영 시간 안내를 검증하고 베타 공개.

중단 조건: 공유 자원 교체/삭제, DB 공개 노출, 비밀 state 유입, 예상 밖 IAM 확대, 미확정 CIDR, 예산 미승인.
Terraform destroy를 배포 rollback 수단으로 쓰지 않는다. 앱은 이전 이미지로, DB는 검증된 복원 경로로 되돌린다.

## 비용 기준과 미결정 사항

2026-09-29 확인한 서울 On-Demand 단가, 월 730시간·세전·할인 미적용 기준:
앱 t4g.medium $30.368 + 앱 gp3 30GB $2.736 + 공인 IPv4 $3.650 + RDS small $37.230 + DB gp3 20GB $2.620 = **$76.604/월**.
이는 신규 기본 자원 소계이며 GPU·기존 서버·Secrets Manager·ECR/S3·추가 백업/전송·관측·CPU 초과 크레딧·세금은 제외한다.
월 총예산 상한, 도메인, 운영 시간, AZ/서브넷 ID, AMI/엔진 버전, 저장소 확장 상한은 별도 확정한다.

## 근거

- [RDS VPC와 DB subnet group](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html)
- [RDS 관리형 master 비밀번호](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html)
- [서울 EC2 공식 가격표](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/ap-northeast-2/index.json)
- [서울 RDS 공식 가격표](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/ap-northeast-2/index.json)
- [공인 IPv4 요금](https://aws.amazon.com/vpc/pricing/)
- [기존 적용 역할 제한](use-terraform-apply-role.md), [관리 경계](aws-management-boundary.md)
