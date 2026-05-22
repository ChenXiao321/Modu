from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract interface for LLM-based structured requirement extraction."""

    @abstractmethod
    def extract_requirements(self, document_text: str, filename: str) -> list[dict]:
        """
        Extract structured requirements from raw document text.

        Returns a list of requirement dicts, each with keys:
        - requirement_id: str
        - description: str
        - chapter: str | None
        - asil_level: str | None
        - parent_requirement_id: str | None
        - children: list[dict] (nested requirements)
        """
        ...

    @abstractmethod
    def extract_safety_parameters(self, document_text: str, filename: str) -> list[dict]:
        """
        Extract safety-critical parameters from raw document text.

        Returns a list of parameter dicts, each with keys:
        - parameter_id: str (e.g., SW-REQ-SAF-001)
        - name: str
        - value: str
        - unit: str | None
        - tolerance: str | None
        - chapter: str | None
        - source_page: int | None
        """
        ...

    @abstractmethod
    def extract_ocr_fields(self, document_text: str, filename: str) -> list[dict]:
        """
        Extract OCR fields with confidence scores from document text.

        Returns a list of field dicts, each with keys:
        - field_id: str (e.g., OCR-FIELD-0001)
        - extracted_text: str
        - normalized_value: str | None
        - confidence: float (0.0-1.0)
        - field_type: str | None (voltage, temperature, timing, etc.)
        - source_page: int | None
        """
        ...

    @abstractmethod
    def generate_design_document(
        self,
        requirements: list[dict],
        safety_parameters: list[dict],
        asil_level: str | None,
        filename: str,
    ) -> dict:
        """
        Generate an ASPICE Level 2 design document from structured requirements.

        Returns a dict with section keys, each containing:
        - content: str
        - polarion_trace_id: str

        Sections: overview, references, system_architecture, interface_definition,
        dynamic_behavior, resource_consumption, error_handling, test_strategy
        """
        ...


class MockLLMClient(LLMClient):
    """
    Mock LLM client for MVP development and testing.
    Returns deterministic simulated requirements based on document text length.
    """

    def extract_requirements(self, document_text: str, filename: str) -> list[dict]:
        text_length = len(document_text)
        base_id = f"SW-REQ-{text_length % 1000:03d}"

        return [
            {
                "requirement_id": base_id,
                "description": (
                    f"System shall process input signals from {filename} "
                    f"with deterministic timing constraints."
                ),
                "chapter": "3.1",
                "asil_level": "B",
                "parent_requirement_id": None,
                "children": [
                    {
                        "requirement_id": f"{base_id}-01",
                        "description": (
                            "The module shall initialize all hardware registers "
                            "to safe default values within 100ms after power-on."
                        ),
                        "chapter": "3.1.1",
                        "asil_level": "B",
                        "parent_requirement_id": base_id,
                        "children": [],
                    },
                    {
                        "requirement_id": f"{base_id}-02",
                        "description": (
                            "The module shall monitor supply voltage and trigger "
                            "safe state if voltage drops below 4.5V."
                        ),
                        "chapter": "3.1.2",
                        "asil_level": "B",
                        "parent_requirement_id": base_id,
                        "children": [],
                    },
                ],
            },
            {
                "requirement_id": f"{base_id}-FUNC",
                "description": (
                    "System shall provide diagnostic interface for fault detection "
                    "and reporting via standard UDS services."
                ),
                "chapter": "4.2",
                "asil_level": None,
                "parent_requirement_id": None,
                "children": [
                    {
                        "requirement_id": f"{base_id}-FUNC-01",
                        "description": (
                            "DTC shall be stored in non-volatile memory "
                            "with timestamp and occurrence counter."
                        ),
                        "chapter": "4.2.1",
                        "asil_level": None,
                        "parent_requirement_id": f"{base_id}-FUNC",
                        "children": [],
                    }
                ],
            },
        ]

    def extract_safety_parameters(self, document_text: str, filename: str) -> list[dict]:
        """Return deterministic mock safety-critical parameters."""
        # Seed-based deterministic selection to keep tests stable
        text_length = len(document_text)

        parameters = [
            {
                "parameter_id": "SW-REQ-SAF-001",
                "name": "供电电压阈值",
                "value": "4.5",
                "unit": "V",
                "tolerance": "±0.1",
                "chapter": "3.2.1",
                "source_page": 42,
            },
            {
                "parameter_id": "SW-REQ-SAF-002",
                "name": "工作温度范围",
                "value": "-40 ~ 150",
                "unit": "°C",
                "tolerance": None,
                "chapter": "3.2.2",
                "source_page": 43,
            },
            {
                "parameter_id": "SW-REQ-SAF-003",
                "name": "看门狗喂狗周期",
                "value": "50",
                "unit": "ms",
                "tolerance": "±5",
                "chapter": "3.3.1",
                "source_page": 48,
            },
            {
                "parameter_id": "SW-REQ-SAF-004",
                "name": "初始化超时时间",
                "value": "100",
                "unit": "ms",
                "tolerance": "+10/-0",
                "chapter": "3.1.1",
                "source_page": 38,
            },
        ]

        # Deterministically return a subset; short/empty docs may get zero params
        count = min(len(parameters), text_length % 4)
        return parameters[:count]

    def extract_ocr_fields(self, document_text: str, filename: str) -> list[dict]:
        """Return deterministic mock OCR fields with confidence scores."""
        text_length = len(document_text)

        fields = [
            {
                "field_id": "OCR-FIELD-0001",
                "extracted_text": "4.5V ±0.1",
                "normalized_value": "4.5",
                "confidence": 0.98,
                "field_type": "voltage",
                "source_page": 42,
            },
            {
                "field_id": "OCR-FIELD-0002",
                "extracted_text": "-40 ~ 150°C",
                "normalized_value": "-40~150",
                "confidence": 0.96,
                "field_type": "temperature",
                "source_page": 43,
            },
            {
                "field_id": "OCR-FIELD-0003",
                "extracted_text": "50 ms (±5)",
                "normalized_value": "50",
                "confidence": 0.72,
                "field_type": "timing",
                "source_page": 48,
            },
            {
                "field_id": "OCR-FIELD-0004",
                "extracted_text": "l00ms init timeout",
                "normalized_value": "100",
                "confidence": 0.65,
                "field_type": "timing",
                "source_page": 38,
            },
            {
                "field_id": "OCR-FIELD-0005",
                "extracted_text": "3.3V reference",
                "normalized_value": "3.3",
                "confidence": 0.91,
                "field_type": "voltage",
                "source_page": 45,
            },
        ]

        # Return a stable subset for testing: always return fields 1-3 to ensure
        # both high-confidence and low-confidence fields are present.
        count = min(len(fields), 3)
        return fields[:count]

    def generate_design_document(
        self,
        requirements: list[dict],
        safety_parameters: list[dict],
        asil_level: str | None,
        filename: str,
    ) -> dict:
        """Return a deterministic mock design document for MVP development."""
        effective_asil = asil_level or "QM"
        base_trace = f"POL-DSGN-{len(filename) % 1000:03d}"

        req_summary = "\n".join(
            f"- {r.get('requirement_id', 'N/A')}: {r.get('description', '')[:80]}"
            for r in requirements[:3]
        )
        param_summary = "\n".join(
            f"- {p.get('parameter_id', 'N/A')}: {p.get('name', '')} = {p.get('value', '')} {p.get('unit', '')}"
            for p in safety_parameters[:3]
        )

        return {
            "overview": {
                "content": (
                    f"本文档描述基于 {filename} 的软件模块设计方案。\n"
                    f"模块 ASIL 等级声明: ASIL-{effective_asil}。\n"
                    f"设计目标: 实现芯片手册定义的功能需求，满足车规级安全与可靠性要求。"
                ),
                "polarion_trace_id": f"{base_trace}-001",
            },
            "references": {
                "content": (
                    "[1] 上游输入文档: 芯片手册 / 需求规格\n"
                    "[2] AUTOSAR Classic Platform 标准 (R20-11)\n"
                    "[3] MISRA C:2012 编码规范\n"
                    "[4] ASPICE Level 2 过程要求"
                ),
                "polarion_trace_id": f"{base_trace}-002",
            },
            "system_architecture": {
                "content": (
                    "模块采用分层架构设计:\n"
                    "- 应用层: 实现业务逻辑与状态机\n"
                    "- 服务层: 封装硬件访问接口\n"
                    "- MCAL 层: 通过标准化接口调用微控制器驱动\n"
                    f"安全机制: 针对 ASIL-{effective_asil} 等级注入看门狗监控与冗余检查。"
                ),
                "polarion_trace_id": f"{base_trace}-003",
            },
            "interface_definition": {
                "content": (
                    "公共接口:\n"
                    "- Modu_<Module>_Init(void): 模块初始化\n"
                    "- Modu_<Module>_MainFunction(void): 周期主函数\n"
                    "- Modu_<Module>_GetVersionInfo(Std_VersionInfoType* versioninfo): 版本查询\n"
                    "回调接口: 通过配置结构体注入，便于单元测试 Mock。"
                ),
                "polarion_trace_id": f"{base_trace}-004",
            },
            "dynamic_behavior": {
                "content": (
                    "状态机定义:\n"
                    "- INIT: 上电初始化，配置寄存器为安全默认值\n"
                    "- RUNNING: 正常业务处理周期\n"
                    "- SAFE_STATE: 故障检测后进入安全状态\n"
                    "状态转换由外部事件或内部超时触发，转换条件在配置头文件中定义。"
                ),
                "polarion_trace_id": f"{base_trace}-005",
            },
            "resource_consumption": {
                "content": (
                    "资源消耗估算 (TC38x 目标):\n"
                    "- ROM: ~8 KB (代码 + 常量表)\n"
                    "- RAM: ~2 KB (全局变量 + 运行时缓冲区)\n"
                    "- 堆栈: 最大深度估计 512 字节\n"
                    "- CPU 负载: 主函数周期 10ms，单次执行 < 500 µs"
                ),
                "polarion_trace_id": f"{base_trace}-006",
            },
            "error_handling": {
                "content": (
                    "错误处理策略:\n"
                    "- 检测到电压异常: 触发 SAFE_STATE，记录 DTC\n"
                    "- 看门狗超时: 触发系统复位\n"
                    "- 非法寄存器访问: 返回 E_NOT_OK，不上报致命错误\n"
                    "所有错误处理路径均具备独立的测试覆盖。"
                ),
                "polarion_trace_id": f"{base_trace}-007",
            },
            "test_strategy": {
                "content": (
                    "测试策略覆盖:\n"
                    "- 单元测试: 基于 Mock/Stub 环境，覆盖所有公共接口\n"
                    "- 边界测试: 数值型参数最小值、最大值、典型值\n"
                    "- 故障注入: 通信超时、电源异常、看门狗复位\n"
                    f"覆盖率目标: 语句 ≥ {90 if effective_asil == 'B' else 80}%，分支 ≥ 80%。"
                ),
                "polarion_trace_id": f"{base_trace}-008",
            },
        }
