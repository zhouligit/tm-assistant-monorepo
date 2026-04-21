import {
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useState } from "react";

import {
  approveKbCandidate,
  ApiError,
  clearAccessToken,
  claimHandoff,
  closeHandoff,
  createKnowledgeSource,
  getAccessToken,
  getHandoffQueue,
  getHealth,
  getKbCandidates,
  getKnowledgeSources,
  getMe,
  login,
  onAuthExpired,
  rejectKbCandidate,
  replyHandoff,
  setAccessToken,
  type CandidateRejectInput,
  type KbCandidateItem,
  type LoginInput,
  type KnowledgeSourceCreateInput,
  type HandoffReplyInput,
  type HandoffQueueItem,
  type KnowledgeSourceItem,
} from "./api";

const { Title, Text, Paragraph } = Typography;
const REQUEST_HISTORY_STORAGE_KEY = "tm_console_request_history_v1";
type RequestHistoryItem = {
  key: string;
  time: string;
  path: string;
  status: string;
  requestId: string;
};

export default function App() {
  const [authed, setAuthed] = useState<boolean>(Boolean(getAccessToken()));
  const [currentUser, setCurrentUser] = useState<{ name: string; role: string } | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);
  const [output, setOutput] = useState<string>("点击按钮开始联调");
  const [lastRequestId, setLastRequestId] = useState<string>("-");
  const [requestHistory, setRequestHistory] = useState<RequestHistoryItem[]>([]);
  const [historyOnlyFailed, setHistoryOnlyFailed] = useState(false);
  const copyRequestId = async () => {
    if (!lastRequestId || lastRequestId === "-") {
      message.warning("当前没有可复制的 request_id");
      return;
    }
    try {
      await navigator.clipboard.writeText(lastRequestId);
      message.success("request_id 已复制");
    } catch {
      message.error("复制失败，请手动复制");
    }
  };

  const copySpecificRequestId = async (value: string) => {
    if (!value || value === "-") return;
    try {
      await navigator.clipboard.writeText(value);
      message.success("request_id 已复制");
    } catch {
      message.error("复制失败，请手动复制");
    }
  };

  const pushHistory = (item: Omit<RequestHistoryItem, "key">) => {
    setRequestHistory((prev) => [{ key: `${Date.now()}-${Math.random()}`, ...item }, ...prev.slice(0, 9)]);
  };
  const clearHistory = () => {
    setRequestHistory([]);
    message.success("请求历史已清空");
  };

  const [loading, setLoading] = useState(false);
  const [knowledgeRows, setKnowledgeRows] = useState<KnowledgeSourceItem[]>([]);
  const [handoffRows, setHandoffRows] = useState<HandoffQueueItem[]>([]);
  const [healthStatus, setHealthStatus] = useState<string>("-");
  const [candidateRows, setCandidateRows] = useState<KbCandidateItem[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [handoffActionLoadingId, setHandoffActionLoadingId] = useState<string | null>(null);
  const [candidateActionLoadingId, setCandidateActionLoadingId] = useState<string | null>(null);
  const [replyOpen, setReplyOpen] = useState(false);
  const [replyLoading, setReplyLoading] = useState(false);
  const [activeHandoffId, setActiveHandoffId] = useState<string | null>(null);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectLoading, setRejectLoading] = useState(false);
  const [activeCandidateId, setActiveCandidateId] = useState<string | null>(null);
  const [form] = Form.useForm<KnowledgeSourceCreateInput>();
  const [replyForm] = Form.useForm<HandoffReplyInput>();
  const [rejectForm] = Form.useForm<CandidateRejectInput>();
  const [loginForm] = Form.useForm<LoginInput>();

  useEffect(() => {
    return onAuthExpired(() => {
      setAuthed(false);
      setCurrentUser(null);
      setOutput("登录已过期，请重新登录");
    });
  }, []);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(REQUEST_HISTORY_STORAGE_KEY);
      if (!saved) return;
      const parsed: unknown = JSON.parse(saved);
      if (!Array.isArray(parsed)) return;
      const normalized = parsed
        .filter((item): item is RequestHistoryItem => {
          if (typeof item !== "object" || item === null) return false;
          const target = item as Partial<RequestHistoryItem>;
          return (
            typeof target.key === "string" &&
            typeof target.time === "string" &&
            typeof target.path === "string" &&
            typeof target.status === "string" &&
            typeof target.requestId === "string"
          );
        })
        .slice(0, 10);
      setRequestHistory(normalized);
    } catch {
      localStorage.removeItem(REQUEST_HISTORY_STORAGE_KEY);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(REQUEST_HISTORY_STORAGE_KEY, JSON.stringify(requestHistory.slice(0, 10)));
  }, [requestHistory]);

  useEffect(() => {
    const bootstrapAuth = async () => {
      if (!authed) {
        return;
      }
      try {
        const res = await getMe();
        setCurrentUser({
          name: res.data?.name ?? "unknown",
          role: res.data?.role ?? "unknown",
        });
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          clearAccessToken();
          setAuthed(false);
          setCurrentUser(null);
          setOutput("登录已过期，请重新登录");
          return;
        }
        setOutput(`初始化用户失败: ${String(err)}`);
      }
    };
    void bootstrapAuth();
  }, [authed]);

  const knowledgeColumns: ColumnsType<KnowledgeSourceItem> = useMemo(
    () => [
      { title: "ID", dataIndex: "id", key: "id", width: 160 },
      { title: "名称", dataIndex: "name", key: "name" },
      { title: "类型", dataIndex: "type", key: "type", width: 120 },
      {
        title: "状态",
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (status: string) => <Tag>{status || "-"}</Tag>,
      },
    ],
    []
  );

  const handleClaim = async (handoffId: string) => {
    try {
      setHandoffActionLoadingId(handoffId);
      const res = await claimHandoff(handoffId);
      setOutput(JSON.stringify(res, null, 2));
      await runHandoff();
    } catch (err) {
      setOutput(`认领失败: ${String(err)}`);
    } finally {
      setHandoffActionLoadingId(null);
    }
  };

  const handleClose = async (handoffId: string) => {
    try {
      setHandoffActionLoadingId(handoffId);
      const res = await closeHandoff(handoffId);
      setOutput(JSON.stringify(res, null, 2));
      await runHandoff();
    } catch (err) {
      setOutput(`关闭失败: ${String(err)}`);
    } finally {
      setHandoffActionLoadingId(null);
    }
  };

  const openReplyModal = (handoffId: string) => {
    setActiveHandoffId(handoffId);
    setReplyOpen(true);
  };

  const submitReply = async () => {
    if (!activeHandoffId) {
      return;
    }
    try {
      const values = await replyForm.validateFields();
      setReplyLoading(true);
      const res = await replyHandoff(activeHandoffId, values);
      setOutput(JSON.stringify(res, null, 2));
      setReplyOpen(false);
      replyForm.resetFields();
      await runHandoff();
    } catch (err) {
      setOutput(`回复失败: ${String(err)}`);
    } finally {
      setReplyLoading(false);
    }
  };

  const handoffColumns: ColumnsType<HandoffQueueItem> = useMemo(
    () => [
      { title: "Handoff ID", dataIndex: "id", key: "id", width: 160 },
      { title: "Session ID", dataIndex: "session_id", key: "session_id", width: 160 },
      {
        title: "状态",
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (status: string) => <Tag color="blue">{status || "-"}</Tag>,
      },
      { title: "原因", dataIndex: "reason", key: "reason" },
      {
        title: "操作",
        key: "actions",
        width: 280,
        render: (_, record) => (
          <Space>
            <Button
              size="small"
              onClick={() => handleClaim(record.id)}
              loading={handoffActionLoadingId === record.id}
            >
              Claim
            </Button>
            <Button
              size="small"
              type="primary"
              onClick={() => openReplyModal(record.id)}
              loading={handoffActionLoadingId === record.id}
            >
              Reply
            </Button>
            <Button
              size="small"
              danger
              onClick={() => handleClose(record.id)}
              loading={handoffActionLoadingId === record.id}
            >
              Close
            </Button>
          </Space>
        ),
      },
    ],
    [handoffActionLoadingId]
  );

  const openRejectModal = (candidateId: string) => {
    setActiveCandidateId(candidateId);
    setRejectOpen(true);
  };

  const handleApproveCandidate = async (candidateId: string) => {
    try {
      setCandidateActionLoadingId(candidateId);
      const res = await approveKbCandidate(candidateId);
      setOutput(JSON.stringify(res, null, 2));
      await runCandidates();
    } catch (err) {
      setOutput(`审核通过失败: ${String(err)}`);
    } finally {
      setCandidateActionLoadingId(null);
    }
  };

  const submitRejectCandidate = async () => {
    if (!activeCandidateId) {
      return;
    }
    try {
      const values = await rejectForm.validateFields();
      setRejectLoading(true);
      const res = await rejectKbCandidate(activeCandidateId, values);
      setOutput(JSON.stringify(res, null, 2));
      setRejectOpen(false);
      rejectForm.resetFields();
      await runCandidates();
    } catch (err) {
      setOutput(`驳回失败: ${String(err)}`);
    } finally {
      setRejectLoading(false);
    }
  };

  const candidateColumns: ColumnsType<KbCandidateItem> = useMemo(
    () => [
      { title: "Candidate ID", dataIndex: "id", key: "id", width: 180 },
      { title: "问题", dataIndex: "question", key: "question" },
      {
        title: "状态",
        dataIndex: "status",
        key: "status",
        width: 120,
        render: (status: string) => <Tag color="purple">{status || "-"}</Tag>,
      },
      {
        title: "操作",
        key: "actions",
        width: 200,
        render: (_, record) => (
          <Space>
            <Button
              size="small"
              type="primary"
              onClick={() => handleApproveCandidate(record.id)}
              loading={candidateActionLoadingId === record.id}
            >
              Approve
            </Button>
            <Button
              size="small"
              danger
              onClick={() => openRejectModal(record.id)}
              loading={candidateActionLoadingId === record.id}
            >
              Reject
            </Button>
          </Space>
        ),
      },
    ],
    [candidateActionLoadingId]
  );

  const filteredRequestHistory = useMemo(() => {
    if (!historyOnlyFailed) return requestHistory;
    return requestHistory.filter((item) => item.status.startsWith("HTTP "));
  }, [historyOnlyFailed, requestHistory]);

  const run = async (fn: () => Promise<unknown>, pathLabel: string) => {
    try {
      setLoading(true);
      const data = await fn();
      let reqId = "-";
      if (
        typeof data === "object" &&
        data !== null &&
        "request_id" in data &&
        typeof (data as { request_id?: unknown }).request_id === "string"
      ) {
        reqId = (data as { request_id: string }).request_id;
        setLastRequestId(reqId);
      }
      pushHistory({
        time: new Date().toLocaleTimeString(),
        path: pathLabel,
        status: "OK",
        requestId: reqId,
      });
      setOutput(JSON.stringify(data, null, 2));
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.detail ? ` (${err.detail})` : "";
        const req = err.requestId ? ` [request_id=${err.requestId}]` : "";
        const bizCode = typeof err.code === "number" ? ` [code=${err.code}]` : "";
        if (err.requestId) {
          setLastRequestId(err.requestId);
        }
        pushHistory({
          time: new Date().toLocaleTimeString(),
          path: err.path ?? "unknown",
          status: `HTTP ${err.status}`,
          requestId: err.requestId ?? "-",
        });
        setOutput(`请求失败: HTTP ${err.status}${bizCode} ${err.message}${detail}${req}`);
      } else {
        setOutput(`请求失败: ${String(err)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const submitLogin = async () => {
    try {
      const values = await loginForm.validateFields();
      setLoginLoading(true);
      const res = await login(values);
      if (!res.data?.access_token) {
        throw new Error("登录响应缺少 access_token");
      }
      setAccessToken(res.data.access_token);
      setAuthed(true);
      setLastRequestId(res.request_id ?? "-");
      pushHistory({
        time: new Date().toLocaleTimeString(),
        path: "/api/v1/tm/auth/login",
        status: "OK",
        requestId: res.request_id ?? "-",
      });
      await getMe().then((meRes) => {
        setCurrentUser({
          name: meRes.data?.name ?? "unknown",
          role: meRes.data?.role ?? "unknown",
        });
      });
      setOutput(JSON.stringify(res, null, 2));
    } catch (err) {
      if (err instanceof ApiError) {
        const detail = err.detail ? ` (${err.detail})` : "";
        const req = err.requestId ? ` [request_id=${err.requestId}]` : "";
        const bizCode = typeof err.code === "number" ? ` [code=${err.code}]` : "";
        if (err.requestId) {
          setLastRequestId(err.requestId);
        }
        pushHistory({
          time: new Date().toLocaleTimeString(),
          path: err.path ?? "/api/v1/tm/auth/login",
          status: `HTTP ${err.status}`,
          requestId: err.requestId ?? "-",
        });
        setOutput(`登录失败: HTTP ${err.status}${bizCode} ${err.message}${detail}${req}`);
      } else {
        setOutput(`登录失败: ${String(err)}`);
      }
    } finally {
      setLoginLoading(false);
    }
  };

  const runMe = async () => {
    await run(async () => {
      const res = await getMe();
      setCurrentUser({
        name: res.data?.name ?? "unknown",
        role: res.data?.role ?? "unknown",
      });
      return res;
    }, "/api/v1/tm/auth/me");
  };

  const handleLogout = () => {
    clearAccessToken();
    setAuthed(false);
    setCurrentUser(null);
    setOutput("已登出");
  };

  const runHealth = async () => {
    await run(async () => {
      const res = await getHealth();
      setHealthStatus(res.data?.status ?? "-");
      return res;
    }, "/api/v1/tm/health");
  };

  const runKnowledge = async () => {
    await run(async () => {
      const res = await getKnowledgeSources();
      const rows = res.data?.list ?? res.data?.items ?? [];
      setKnowledgeRows(rows);
      return res;
    }, "/api/v1/tm/knowledge/sources");
  };

  const runHandoff = async () => {
    await run(async () => {
      const res = await getHandoffQueue();
      const rows = res.data?.list ?? res.data?.items ?? [];
      setHandoffRows(rows);
      return res;
    }, "/api/v1/tm/handoff/tickets");
  };

  const runCandidates = async () => {
    await run(async () => {
      const res = await getKbCandidates("pending");
      const rows = res.data?.list ?? res.data?.items ?? [];
      setCandidateRows(rows);
      return res;
    }, "/api/v1/tm/knowledge/kb-candidates");
  };

  const submitCreateKnowledgeSource = async () => {
    try {
      const values = await form.validateFields();
      setCreateLoading(true);
      const payload: KnowledgeSourceCreateInput = {
        ...values,
        tags: values.tags ?? [],
      };
      const res = await createKnowledgeSource(payload);
      setOutput(JSON.stringify(res, null, 2));
      setCreateOpen(false);
      form.resetFields();
      await runKnowledge();
    } catch (err) {
      setOutput(`创建知识源失败: ${String(err)}`);
    } finally {
      setCreateLoading(false);
    }
  };

  if (!authed) {
    return (
      <div style={{ maxWidth: 520, margin: "80px auto", padding: "0 16px" }}>
        <Card title="TM Console 登录">
          <Form
            form={loginForm}
            layout="vertical"
            initialValues={{ email: "admin@demo.com", password: "123456" }}
          >
            <Form.Item name="email" label="邮箱" rules={[{ required: true, message: "请输入邮箱" }]}>
              <Input />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[{ required: true, message: "请输入密码" }]}
            >
              <Input.Password />
            </Form.Item>
            <Button type="primary" loading={loginLoading} onClick={submitLogin}>
              登录
            </Button>
          </Form>
          <Paragraph style={{ marginTop: 16, marginBottom: 0 }} type="secondary">
            MVP 默认账号：admin@demo.com / 123456
          </Paragraph>
        </Card>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: "24px auto", padding: "0 16px" }}>
      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Space align="center" style={{ justifyContent: "space-between", width: "100%" }}>
          <Title level={3} style={{ margin: 0 }}>
            TM Console 联调页
          </Title>
          <Space>
            <Text type="secondary">
              当前用户：{currentUser?.name ?? "-"} / {currentUser?.role ?? "-"}
            </Text>
            <Button onClick={runMe}>刷新用户</Button>
            <Button danger onClick={handleLogout}>
              退出登录
            </Button>
          </Space>
        </Space>
        <Text type="secondary">默认请求网关: http://127.0.0.1:18000</Text>
        <Space>
          <Text type="secondary">最近 request_id: {lastRequestId}</Text>
          <Button size="small" onClick={copyRequestId}>
            复制 request_id
          </Button>
        </Space>
        <Card>
          <Space wrap>
            <Button loading={loading} onClick={runHealth}>
              Health
            </Button>
            <Button loading={loading} onClick={runKnowledge}>
              Knowledge Sources
            </Button>
            <Button loading={loading} onClick={runHandoff}>
              Handoff Queue
            </Button>
            <Button loading={loading} onClick={runCandidates}>
              KB Candidates
            </Button>
          </Space>
          <div style={{ marginTop: 12 }}>
            <Text>Health: </Text>
            <Tag color={healthStatus === "ok" ? "green" : "default"}>{healthStatus}</Tag>
          </div>
        </Card>
        <Card
          title="Knowledge Sources"
          extra={
            <Button type="primary" onClick={() => setCreateOpen(true)}>
              新增知识源
            </Button>
          }
        >
          <Table
            rowKey="id"
            columns={knowledgeColumns}
            dataSource={knowledgeRows}
            pagination={{ pageSize: 8 }}
            size="small"
          />
        </Card>
        <Card title="Handoff Queue">
          <Table
            rowKey="id"
            columns={handoffColumns}
            dataSource={handoffRows}
            pagination={{ pageSize: 8 }}
            size="small"
          />
        </Card>
        <Card title="Knowledge Base Candidates">
          <Table
            rowKey="id"
            columns={candidateColumns}
            dataSource={candidateRows}
            pagination={{ pageSize: 8 }}
            size="small"
          />
        </Card>
        <Card title="响应结果">
          <Paragraph>
            <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{output}</pre>
          </Paragraph>
        </Card>
        <Card
          title="请求历史（最近10条）"
          extra={
            <Space>
              <Checkbox checked={historyOnlyFailed} onChange={(e) => setHistoryOnlyFailed(e.target.checked)}>
                仅失败请求
              </Checkbox>
              <Button size="small" danger onClick={clearHistory}>
                清空历史
              </Button>
            </Space>
          }
        >
          <Table<RequestHistoryItem>
            rowKey="key"
            size="small"
            pagination={false}
            dataSource={filteredRequestHistory}
            columns={[
              { title: "时间", dataIndex: "time", key: "time", width: 110 },
              { title: "接口", dataIndex: "path", key: "path" },
              { title: "状态", dataIndex: "status", key: "status", width: 120 },
              {
                title: "request_id",
                dataIndex: "requestId",
                key: "requestId",
                render: (value: string) => (
                  <Space>
                    <Text code>{value}</Text>
                    <Button size="small" onClick={() => copySpecificRequestId(value)}>
                      复制
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Space>

      <Modal
        title="新增知识源"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={submitCreateKnowledgeSource}
        okText="创建"
        confirmLoading={createLoading}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            type: "faq",
            name: "",
            config: { source: "manual" },
            tags: [],
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="例如：售前FAQ" />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true, message: "请选择类型" }]}>
            <Select
              options={[
                { label: "FAQ", value: "faq" },
                { label: "飞书文档", value: "feishu_doc" },
                { label: "网页", value: "web_url" },
                { label: "PDF", value: "pdf" },
              ]}
            />
          </Form.Item>
          <Form.Item
            name={["config", "url"]}
            label="URL（可选）"
            tooltip="飞书文档或网页知识源可填写"
          >
            <Input placeholder="https://..." />
          </Form.Item>
          <Form.Item name="tags" label="标签（逗号分隔）" getValueFromEvent={(e) => {
            const value = e?.target?.value ?? "";
            return value
              .split(",")
              .map((x: string) => x.trim())
              .filter(Boolean);
          }}>
            <Input placeholder="presales,pricing" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`回复接管会话 ${activeHandoffId ?? ""}`}
        open={replyOpen}
        onCancel={() => setReplyOpen(false)}
        onOk={submitReply}
        okText="提交回复"
        confirmLoading={replyLoading}
      >
        <Form
          form={replyForm}
          layout="vertical"
          initialValues={{
            content: "",
            mark_as_kb_candidate: true,
          }}
        >
          <Form.Item
            name="content"
            label="回复内容"
            rules={[{ required: true, message: "请输入回复内容" }]}
          >
            <Input.TextArea rows={4} placeholder="例如：您好，退款通常3-5个工作日到账。" />
          </Form.Item>
          <Form.Item name="mark_as_kb_candidate" valuePropName="checked">
            <Checkbox>标记为知识回流候选</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`驳回候选 ${activeCandidateId ?? ""}`}
        open={rejectOpen}
        onCancel={() => setRejectOpen(false)}
        onOk={submitRejectCandidate}
        okText="确认驳回"
        confirmLoading={rejectLoading}
      >
        <Form
          form={rejectForm}
          layout="vertical"
          initialValues={{
            reason: "",
          }}
        >
          <Form.Item
            name="reason"
            label="驳回原因"
            rules={[{ required: true, message: "请输入驳回原因" }]}
          >
            <Input.TextArea rows={3} placeholder="例如：答案不完整，缺少退款时效说明。" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
