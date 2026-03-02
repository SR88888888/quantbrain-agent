import re
import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from src.core.config import settings
from src.core.logger import log
from src.llm.wrapper import llm_wrapper


class ThoughtStep:
    def __init__(self, step_id: int, thought: str = "", action: str = None,
                 action_input: Dict = None, observation: str = ""):
        self.step_id = step_id
        self.thought = thought
        self.action = action
        self.action_input = action_input
        self.observation = observation

    def to_dict(self):
        return {
            "step": self.step_id, "thought": self.thought,
            "action": self.action, "observation": self.observation[:200],
        }


class ReActEngine:
    """ReAct推理引擎: 思考-行动-观察循环"""

    def __init__(self):
        self.enabled = getattr(settings, "REACT_ENABLED", True)
        self.max_iterations = settings.REACT_MAX_ITERATIONS

    async def reason(
        self,
        task: str,
        context: str,
        tool_executor: Optional[Callable] = None,
        available_tools: str = "",
    ) -> Tuple[str, List[ThoughtStep]]:
        """
        执行ReAct循环

        返回: (最终答案, 思考步骤列表)
        """
        if not self.enabled:
            return "ReAct已禁用", []

        steps: List[ThoughtStep] = []
        history = ""
        system_prompt = self._build_system(available_tools)

        for i in range(self.max_iterations):
            user_prompt = self._build_prompt(task, context, history)
            response = llm_wrapper.generate(user_prompt, system=system_prompt)
            thought, action, action_input, final_answer = self._parse(response)

            step = ThoughtStep(
                step_id=i + 1,
                thought=thought,
                action=action,
                action_input=action_input,
            )

            if final_answer:
                step.observation = f"最终答案: {final_answer}"
                steps.append(step)
                log.debug(f"ReAct完成, 共{i + 1}步")
                return final_answer, steps

            if action and tool_executor:
                try:
                    observation = await tool_executor(action, action_input or {})
                    step.observation = str(observation)[:500]
                except Exception as e:
                    step.observation = f"工具执行错误: {e}"
            else:
                step.observation = "无需执行工具"

            steps.append(step)
            history += self._format_step(step)

            if self._should_stop(steps):
                break

        return self._synthesize(steps), steps

    async def reason_with_mcp(
        self,
        task: str,
        context: str,
    ) -> "tuple[str, list]":
        """使用MCP注册的工具进行ReAct推理"""
        from src.mcp.registry import mcp_registry

        available_tools = mcp_registry.format_for_llm()

        async def mcp_executor(action_name, params):
            return await mcp_registry.invoke(action_name, params)

        return await self.reason(
            task=task, context=context,
            tool_executor=mcp_executor,
            available_tools=available_tools,
        )

    def _build_system(self, available_tools: str) -> str:
        tools_desc = available_tools or "暂无可用工具"
        return (
            "你是专业的金融分析AI,使用ReAct框架推理。\n\n"
            f"可用工具:\n{tools_desc}\n\n"
            "回复格式:\n"
            "Thought: [思考过程]\n"
            "Action: [工具名称, 不需要工具写None]\n"
            "Action Input: [JSON参数]\n\n"
            "或得出结论时:\n"
            "Thought: [最终思考]\n"
            "Final Answer: [最终答案]\n\n"
            "每次只执行一个Action,推理要简洁。"
        )

    def _build_prompt(self, task: str, context: str, history: str) -> str:
        prompt = f"任务: {task}\n\n上下文:\n{context}\n"
        if history:
            prompt += f"\n已执行步骤:\n{history}\n请继续推理。"
        else:
            prompt += "\n请开始分析。"
        return prompt

    def _parse(self, response: str) -> Tuple[str, Optional[str], Optional[Dict], Optional[str]]:
        thought = ""
        action = None
        action_input = None
        final_answer = None

        match = re.search(r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)", response, re.DOTALL)
        if match:
            thought = match.group(1).strip()

        match = re.search(r"Final Answer:\s*(.+?)$", response, re.DOTALL)
        if match:
            return thought, None, None, match.group(1).strip()

        match = re.search(r"Action:\s*(\w+)", response)
        if match:
            action = match.group(1)
            if action.lower() == "none":
                action = None

        match = re.search(r"Action Input:\s*(\{.+?\})", response, re.DOTALL)
        if match:
            try:
                action_input = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return thought, action, action_input, final_answer

    def _format_step(self, step: ThoughtStep) -> str:
        text = f"\n步骤 {step.step_id}:\n"
        text += f"Thought: {step.thought}\n"
        if step.action:
            text += f"Action: {step.action}\n"
            if step.action_input:
                text += f"Action Input: {json.dumps(step.action_input, ensure_ascii=False)}\n"
        if step.observation:
            text += f"Observation: {step.observation}\n"
        return text

    def _should_stop(self, steps: List[ThoughtStep]) -> bool:
        if len(steps) < 2:
            return False
        return all(s.action is None for s in steps[-2:])

    def _synthesize(self, steps: List[ThoughtStep]) -> str:
        if not steps:
            return "无法得出结论"
        thoughts = [s.thought for s in steps if s.thought]
        return thoughts[-1] if thoughts else "分析未完成"


react_engine = ReActEngine()
