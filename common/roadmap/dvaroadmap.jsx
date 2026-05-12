import { useState } from "react";

const phases = [
  {
    id: 1,
    name: "開発基礎 & サーバーレス",
    color: "#1D9E75",
    colorLight: "#E1F5EE",
    weeks: "Week 1–3",
    dates: "5/7 – 5/25",
    hours: "52時間",
    goal: "DVA頻出のLambda・API Gateway・DynamoDBを中心に開発者視点で理解する",
    items: [
      {
        week: "Week 1（5/7–5/11）",
        hours: "12h",
        tasks: [
          { type: "study", text: "DVA試験ガイドを読み、SAAとの出題範囲の違いを整理する（開発・デプロイ・トラブルシュートが重点）" },
          { type: "video", text: "Cloud Tech：「Lambda」セクション視聴（実行モデル、ハンドラ、環境変数、レイヤー、同時実行数）" },
          { type: "hands", text: "AWS Console：Lambda関数をゼロから作成 → 環境変数設定 → CloudWatch Logsでログ確認" },
          { type: "hands", text: "AWS Console：Lambda + S3イベントトリガーで画像アップロード時に自動処理する仕組みを構築" },
        ],
      },
      {
        week: "Week 2（5/12–5/18）",
        hours: "18h",
        tasks: [
          { type: "video", text: "Cloud Tech：「API Gateway」セクション視聴（REST API / HTTP API、ステージ、認可、スロットリング）" },
          { type: "video", text: "Cloud Tech：「DynamoDB（開発者向け）」セクション視聴（パーティションキー設計、GSI/LSI、DynamoDB Streams）" },
          { type: "hands", text: "AWS Console：API Gateway + Lambda + DynamoDB でCRUD APIを構築（サーバーレス三銃士）" },
          { type: "hands", text: "AWS Console：DynamoDB Streams → Lambda でデータ変更時の自動処理を実装" },
          { type: "quiz", text: "Cloud Tech：Lambda / API Gateway / DynamoDB の分野別問題を解く" },
        ],
      },
      {
        week: "Week 3（5/19–5/25）",
        hours: "18h",
        tasks: [
          { type: "video", text: "Cloud Tech：「Step Functions」セクション視聴（ステートマシン、タスク状態、エラーハンドリング、リトライ）" },
          { type: "video", text: "Cloud Tech：「SQS」「SNS」「Kinesis」セクション視聴（開発者向け：メッセージ処理パターン、DLQ）" },
          { type: "hands", text: "AWS Console：SQS → Lambda のポーリング連携を構築 → DLQ（デッドレターキュー）の動作確認" },
          { type: "hands", text: "AWS Console：Step Functionsでワークフローを作成（Lambda関数のオーケストレーション）" },
          { type: "quiz", text: "Cloud Tech：Step Functions / SQS / SNS / Kinesis の分野別問題を解く" },
        ],
      },
    ],
  },
  {
    id: 2,
    name: "CI/CD & デプロイ",
    color: "#378ADD",
    colorLight: "#E6F1FB",
    weeks: "Week 4–5",
    dates: "5/26 – 6/8",
    hours: "36時間",
    goal: "CodeシリーズとIaCツール（CloudFormation / SAM）によるデプロイ戦略を習得する",
    items: [
      {
        week: "Week 4（5/26–6/1）",
        hours: "18h",
        tasks: [
          { type: "video", text: "Cloud Tech：「CodeCommit」「CodeBuild」「CodeDeploy」「CodePipeline」セクション視聴" },
          { type: "study", text: "CodeDeployのデプロイ戦略を整理（In-Place / Blue-Green / Canary / Linear / AllAtOnce）" },
          { type: "hands", text: "AWS Console：CodePipeline を構築（Source → Build → Deploy の一連のCI/CDパイプライン）" },
          { type: "hands", text: "AWS Console：CodeDeployでEC2へのBlue-Greenデプロイを実行 → appspec.ymlの構成を理解" },
          { type: "quiz", text: "Cloud Tech：CI/CD（Codeシリーズ）の分野別問題を解く" },
        ],
      },
      {
        week: "Week 5（6/2–6/8）",
        hours: "18h",
        tasks: [
          { type: "video", text: "Cloud Tech：「CloudFormation」セクション視聴（テンプレート構造、組み込み関数、スタック操作）" },
          { type: "video", text: "Cloud Tech：「SAM（Serverless Application Model）」「Elastic Beanstalk」セクション視聴" },
          { type: "hands", text: "AWS Console：SAMテンプレートでLambda + API Gatewayをデプロイ → sam local invokeでローカルテスト" },
          { type: "study", text: "Elastic Beanstalkのデプロイポリシーを整理（All at once / Rolling / Immutable / Blue-Green）" },
          { type: "quiz", text: "Cloud Tech：CloudFormation / SAM / Elastic Beanstalk の分野別問題を解く" },
        ],
      },
    ],
  },
  {
    id: 3,
    name: "セキュリティ & モニタリング",
    color: "#D85A30",
    colorLight: "#FAECE7",
    weeks: "Week 6–7",
    dates: "6/9 – 6/22",
    hours: "36時間",
    goal: "開発者に必要なセキュリティ知識とデバッグ・監視手法をマスターする",
    items: [
      {
        week: "Week 6（6/9–6/15）",
        hours: "18h",
        tasks: [
          { type: "video", text: "Cloud Tech：「Cognito」セクション視聴（ユーザープール / IDプール / OAuth2.0フロー）" },
          { type: "video", text: "Cloud Tech：「KMS」「Secrets Manager」「Systems Manager Parameter Store」セクション視聴" },
          { type: "study", text: "IAMポリシー評価ロジックを整理（明示的拒否 > 明示的許可 > 暗黙的拒否）" },
          { type: "hands", text: "AWS Console：Cognitoユーザープールでサインアップフローを構築 → API GatewayのCognito認可と連携" },
          { type: "quiz", text: "Cloud Tech：セキュリティ系（Cognito / KMS / IAM開発者向け）の分野別問題を解く" },
        ],
      },
      {
        week: "Week 7（6/16–6/22）",
        hours: "18h",
        tasks: [
          { type: "video", text: "Cloud Tech：「X-Ray」セクション視聴（トレース、セグメント、サブセグメント、サンプリングルール）" },
          { type: "video", text: "Cloud Tech：「CloudWatch」セクション視聴（メトリクス、アラーム、Logs Insights、カスタムメトリクス）" },
          { type: "video", text: "Cloud Tech：「ECS / ECR」「Docker基礎」セクション視聴（タスク定義、サービス、Fargate）" },
          { type: "hands", text: "AWS Console：X-RayをLambda関数に統合 → サービスマップでボトルネックを可視化" },
          { type: "quiz", text: "Cloud Tech：モニタリング / コンテナ系の分野別問題を解く" },
        ],
      },
    ],
  },
  {
    id: 4,
    name: "実戦演習 & 最終仕上げ",
    color: "#534AB7",
    colorLight: "#EEEDFE",
    weeks: "Week 8",
    dates: "6/23 – 6/30",
    hours: "18時間",
    goal: "模擬試験を繰り返し、弱点を潰して合格ラインを確実に超える",
    items: [
      {
        week: "Week 8 前半（6/23–6/26）",
        hours: "8h",
        tasks: [
          { type: "exam", text: "Cloud Tech：DVA模擬試験①を本番同様に65問通しで解く（130分計測）" },
          { type: "study", text: "間違えた問題を全て解説を読み込み → 該当サービスの講義動画に戻って復習" },
          { type: "study", text: "不正解の傾向分析：苦手分野TOP3を特定し、ノートに整理する" },
          { type: "exam", text: "Cloud Tech：DVA模擬試験②を65問通しで解く → 不正解のみ2周目" },
        ],
      },
      {
        week: "Week 8 後半（6/27–6/30 試験日）",
        hours: "10h",
        tasks: [
          { type: "exam", text: "Cloud Tech：DVA模擬試験③を65問通しで解く → 目標：正答率80%以上" },
          { type: "study", text: "全模擬試験の不正解を横断レビュー → デプロイ戦略比較表・暗号化パターン整理シートを作成" },
          { type: "quiz", text: "Cloud Tech：全分野ランダム問題を毎日20問ずつ軽めに解く" },
          { type: "study", text: "試験前日は暗記シートの最終確認のみ → 早めに就寝" },
          { type: "exam", text: "6/30 本番試験！SAAの知識ベースがあるので自信を持って臨む 🎯" },
        ],
      },
    ],
  },
];

const typeConfig = {
  video: { label: "動画", bg: "#E6F1FB", color: "#185FA5", icon: "▶" },
  hands: { label: "ハンズオン", bg: "#E1F5EE", color: "#0F6E56", icon: "⌨" },
  quiz: { label: "問題演習", bg: "#FAEEDA", color: "#854F0B", icon: "✎" },
  exam: { label: "模擬試験", bg: "#FAECE7", color: "#993C1D", icon: "📋" },
  study: { label: "復習整理", bg: "#EEEDFE", color: "#534AB7", icon: "📝" },
};

const saaAdvantages = [
  "VPC / EC2 / S3 / RDS の基礎知識はそのまま活用できる",
  "IAM / セキュリティの基礎は習得済み → Cognito・KMSの上乗せに集中",
  "Well-Architected Frameworkの設計思想を開発者目線で再整理するだけ",
];

export default function DVARoadmap() {
  const [openPhase, setOpenPhase] = useState(1);
  const [openWeek, setOpenWeek] = useState(null);

  return (
    <div style={{ fontFamily: "var(--font-sans, system-ui)", maxWidth: 680, margin: "0 auto", padding: "0 0 2rem" }}>

      {/* Header */}
      <div style={{
        background: "var(--color-background-secondary)",
        borderRadius: "var(--border-radius-lg)",
        padding: "16px 20px",
        marginBottom: 16,
      }}>
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 6 }}>SAA学習経験からのアドバンテージ</div>
        {saaAdvantages.map((a, i) => (
          <div key={i} style={{ fontSize: 13, color: "var(--color-text-primary)", lineHeight: 1.7, paddingLeft: 12, position: "relative" }}>
            <span style={{ position: "absolute", left: 0, color: "var(--color-text-info)" }}>+</span>{a}
          </div>
        ))}
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 24 }}>
        {[
          { label: "学習期間", value: "約8週間" },
          { label: "総学習時間", value: "~142h" },
          { label: "平日 / 休日", value: "2h / 4h" },
          { label: "合格ライン", value: "720/1000" },
        ].map((s, i) => (
          <div key={i} style={{
            background: "var(--color-background-secondary)",
            borderRadius: "var(--border-radius-md)",
            padding: "12px 14px",
          }}>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 18, fontWeight: 500, color: "var(--color-text-primary)" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* DVA vs SAA focus areas */}
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10,
        marginBottom: 24,
      }}>
        <div style={{
          background: "var(--color-background-primary)",
          border: "0.5px solid var(--color-border-tertiary)",
          borderRadius: "var(--border-radius-md)",
          padding: "14px 16px",
        }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: 8 }}>DVA重点分野（SAAと異なる部分）</div>
          {["Lambda / API Gateway 深掘り", "CI/CD（Codeシリーズ）", "CloudFormation / SAM", "X-Ray / デバッグ", "Cognito / SDK操作"].map((t, i) => (
            <div key={i} style={{ fontSize: 13, color: "#185FA5", lineHeight: 1.8 }}>→ {t}</div>
          ))}
        </div>
        <div style={{
          background: "var(--color-background-primary)",
          border: "0.5px solid var(--color-border-tertiary)",
          borderRadius: "var(--border-radius-md)",
          padding: "14px 16px",
        }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-secondary)", marginBottom: 8 }}>SAAからの流用（軽い復習で可）</div>
          {["VPC / EC2 / ELB", "S3 / CloudFront", "RDS / DynamoDB基礎", "IAM 基礎", "CloudWatch 基礎"].map((t, i) => (
            <div key={i} style={{ fontSize: 13, color: "var(--color-text-secondary)", lineHeight: 1.8 }}>✓ {t}</div>
          ))}
        </div>
      </div>

      {/* Timeline */}
      <div style={{ position: "relative" }}>
        {phases.map((phase) => {
          const isOpen = openPhase === phase.id;
          return (
            <div key={phase.id} style={{ marginBottom: 16 }}>
              <div
                onClick={() => setOpenPhase(isOpen ? null : phase.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 14,
                  padding: "14px 18px",
                  background: isOpen ? phase.colorLight : "var(--color-background-primary)",
                  border: `0.5px solid ${isOpen ? phase.color + "44" : "var(--color-border-tertiary)"}`,
                  borderRadius: "var(--border-radius-lg)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                <div style={{
                  width: 36, height: 36, borderRadius: "50%",
                  background: phase.color, color: "#fff",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontWeight: 500, fontSize: 15, flexShrink: 0,
                }}>
                  {phase.id}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, fontSize: 15, color: "var(--color-text-primary)" }}>
                    {phase.name}
                    <span style={{ fontWeight: 400, fontSize: 13, color: "var(--color-text-secondary)", marginLeft: 10 }}>
                      {phase.dates}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 2 }}>
                    {phase.goal}
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: phase.color }}>{phase.hours}</div>
                  <div style={{ fontSize: 12, color: "var(--color-text-tertiary)" }}>{phase.weeks}</div>
                </div>
                <span style={{ fontSize: 13, color: "var(--color-text-secondary)", transition: "transform 0.2s", transform: isOpen ? "rotate(180deg)" : "rotate(0)" }}>
                  ▼
                </span>
              </div>

              {isOpen && (
                <div style={{ marginTop: 8, marginLeft: 18, borderLeft: `2px solid ${phase.color}33`, paddingLeft: 20 }}>
                  {phase.items.map((item, wi) => {
                    const weekKey = `${phase.id}-${wi}`;
                    const isWeekOpen = openWeek === weekKey;
                    return (
                      <div key={wi} style={{ marginBottom: 8 }}>
                        <div
                          onClick={() => setOpenWeek(isWeekOpen ? null : weekKey)}
                          style={{
                            display: "flex", alignItems: "center", justifyContent: "space-between",
                            padding: "10px 14px",
                            background: "var(--color-background-primary)",
                            border: "0.5px solid var(--color-border-tertiary)",
                            borderRadius: "var(--border-radius-md)",
                            cursor: "pointer",
                          }}
                        >
                          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <div style={{
                              width: 8, height: 8, borderRadius: "50%",
                              background: phase.color, flexShrink: 0,
                            }} />
                            <span style={{ fontWeight: 500, fontSize: 14, color: "var(--color-text-primary)" }}>{item.week}</span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>{item.hours}</span>
                            <span style={{ fontSize: 12, color: "var(--color-text-secondary)", transition: "transform 0.2s", transform: isWeekOpen ? "rotate(180deg)" : "rotate(0)" }}>▼</span>
                          </div>
                        </div>

                        {isWeekOpen && (
                          <div style={{ padding: "10px 0 4px 18px" }}>
                            {item.tasks.map((task, ti) => {
                              const tc = typeConfig[task.type];
                              return (
                                <div key={ti} style={{
                                  display: "flex", alignItems: "flex-start", gap: 10,
                                  padding: "8px 0",
                                  borderBottom: ti < item.tasks.length - 1 ? "0.5px solid var(--color-border-tertiary)" : "none",
                                }}>
                                  <span style={{
                                    display: "inline-flex", alignItems: "center", gap: 4,
                                    fontSize: 11, fontWeight: 500,
                                    padding: "2px 8px", borderRadius: 20,
                                    background: tc.bg, color: tc.color,
                                    flexShrink: 0, marginTop: 2,
                                  }}>
                                    {tc.icon} {tc.label}
                                  </span>
                                  <span style={{ fontSize: 13, lineHeight: 1.6, color: "var(--color-text-primary)" }}>
                                    {task.text}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div style={{
        display: "flex", flexWrap: "wrap", gap: 8, marginTop: 20,
        padding: "12px 16px",
        background: "var(--color-background-secondary)",
        borderRadius: "var(--border-radius-md)",
      }}>
        {Object.entries(typeConfig).map(([key, tc]) => (
          <span key={key} style={{
            display: "inline-flex", alignItems: "center", gap: 4,
            fontSize: 12, padding: "3px 10px", borderRadius: 16,
            background: tc.bg, color: tc.color,
          }}>
            {tc.icon} {tc.label}
          </span>
        ))}
      </div>
    </div>
  );
}