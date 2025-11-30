# Streamlit 메모리 문제 해결 가이드

## 문제점 분석

Streamlit 환경에서 메모리가 제대로 작동하지 않는 이유:

1. **@st.cache_resource의 캐싱 방식**
   - `create_paca_agent(paca_version)`이 같은 `paca_version` 인자로 호출되면 캐싱된 결과를 반환합니다.
   - 이는 메모리도 캐싱된다는 뜻입니다. ✓ 이것은 우리가 원하는 동작입니다.

2. **실제 문제: 메모리 객체의 생명주기**
   - 문제는 `sp_memory`를 저장하지 않는 것입니다.
   - `Experiment_claude_basic.py` line 97-102에서:
     ```python
     sp_agent, sp_memory = create_conversational_agent(...)  # sp_memory를 저장하지 않음!
     ```

3. **또 다른 문제: 세션 상태 관리**
   - `paca_agent`는 클로저 내의 `memory` 객체를 참조합니다.
   - `st.session_state`에 저장되지만, 페이지 리로드 시 새로운 `create_paca_agent` 호출이 발생할 수 있습니다.

## 해결 방법

### 방법 1: 메모리를 반환 값에 포함시키기 (권장)
`create_paca_agent`와 `create_conversational_agent`에서 메모리를 명시적으로 반환하고 저장합니다.

### 방법 2: 세션 상태에서 메모리 검증하기
메모리가 올바르게 유지되고 있는지 확인하는 디버깅 코드를 추가합니다.

## 현재 상태

✓ 모든 에이전트 생성 함수에 `@st.cache_resource` 데코레이터 추가됨
✓ 메모리 객체를 리스트로 변환하여 chain.invoke() 호출 시 전달

## 추가 필요한 수정사항

1. `Experiment_claude_basic.py` (및 다른 Experiment 파일들)에서:
   - `sp_memory`도 명시적으로 저장하기
   - 메모리 상태 확인용 디버깅 코드 추가

2. `simulate_conversation` 함수:
   - 같은 에이전트와 메모리를 지속적으로 사용하도록 보장
