"""
PromptShield - Streamlit Dashboard
Four tabs: Red vs Blue | Benchmark | Adaptive Attack | Live Target + Auto Report
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from src.red_team  import RedTeamAgent
from src.blue_team import BlueTeamAgent
from src.evaluator import Evaluator
from src.victim    import VictimLLM
from src.reporter  import DefenseReporter

st.set_page_config(page_title="PromptShield", layout="wide")

for k, v in [("attacks", []), ("results", []), ("evaluator", None),
             ("ran_defense", False), ("adaptive_pairs", []),
             ("live_results", []), ("live_report", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

st.title("PromptShield")
st.markdown(
    "LLM Red vs Blue Team — Prompt Injection Attack and Defense System  \n"
    "Red Team: Google Gemini  |  Blue Team: NVIDIA NIM Llama 3.3  |  Victim: Simulated Enterprise LLM"
)
st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "Red vs Blue",
    "Benchmark",
    "Adaptive Attack",
    "Live Target + Report"
])


# ── shared results block ────────────────────────────────────────────────────
def show_results(ev, df):
    metrics = ev.calculate_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy",  f"{metrics['accuracy']:.1%}")
    c2.metric("Precision", f"{metrics['precision']:.1%}")
    c3.metric("Recall",    f"{metrics['recall']:.1%}")
    c4.metric("F1 Score",  f"{metrics['f1_score']:.1%}")

    ch1, ch2 = st.columns(2)
    with ch1:
        tc = df["attack_type"].value_counts()
        st.plotly_chart(
            px.pie(values=tc.values, names=tc.index, title="Attack Type Distribution", hole=0.3),
            use_container_width=True)
    with ch2:
        sev_order = ["critical", "high", "medium", "low", "none"]
        sc   = df["severity"].value_counts().reindex(sev_order, fill_value=0)
        cmap = {"critical":"#d62728","high":"#ff7f0e","medium":"#ffdd57","low":"#2ca02c","none":"#aec7e8"}
        fig  = px.bar(x=sc.index, y=sc.values, color=sc.index,
                      color_discrete_map=cmap, title="Severity Distribution")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("MITRE ATT&CK Mapping")
    mcols = ["input", "attack_type", "mitre_technique_id", "mitre_technique_name", "severity"]
    st.dataframe(df[[c for c in mcols if c in df.columns]], use_container_width=True)

    st.subheader("Full Results")
    show = ["input", "predicted_attack", "attack_type", "confidence",
            "severity", "mitre_technique_id", "explanation"]
    st.dataframe(df[[c for c in show if c in df.columns]], use_container_width=True)


# ═══════════════════════════════════════════════════════════
# TAB 1 — Red vs Blue
# ═══════════════════════════════════════════════════════════
with tab1:
    with st.sidebar:
        st.header("Settings")
        num_attacks  = st.slider("Attacks to generate", 3, 10, 5)
        red_version  = st.selectbox("Red Team Prompt",  ["v1", "v2"])
        blue_version = st.selectbox("Blue Team Prompt", ["v1", "v2"])
        st.caption("v1 = zero-shot  |  v2 = chain-of-thought")

    left, right = st.columns(2)

    with left:
        st.header("Red Team (Gemini)")
        system_desc = st.text_area(
            "Describe the target LLM system:",
            placeholder="e.g. A banking chatbot that can access account info and process transactions.",
            height=120)

        if st.button("Generate Attacks", type="primary"):
            if not system_desc.strip():
                st.warning("Please describe the target system first.")
            else:
                with st.spinner("Gemini is generating attacks..."):
                    agent = RedTeamAgent(prompt_version=red_version)
                    st.session_state.attacks     = agent.generate_attacks(system_desc, num_attacks)
                    st.session_state.ran_defense = False
                st.success(f"{len(st.session_state.attacks)} attacks generated.")

        for i, atk in enumerate(st.session_state.attacks, 1):
            with st.expander(f"Attack {i}"):
                st.code(atk["text"], language="text")

    with right:
        st.header("Blue Team (NVIDIA NIM)")
        if not st.session_state.attacks:
            st.info("Generate attacks first.")
        else:
            if st.button("Run Defense Analysis", type="secondary"):
                ev   = Evaluator()
                bar  = st.progress(0)
                blue = BlueTeamAgent(prompt_version=blue_version)
                for i, atk in enumerate(st.session_state.attacks):
                    with st.spinner(f"Analyzing {i+1}/{len(st.session_state.attacks)}..."):
                        result = blue.analyze(atk["text"])
                        ev.add_result(atk["text"], result, ground_truth=True)
                    bar.progress((i+1) / len(st.session_state.attacks))
                st.session_state.evaluator   = ev
                st.session_state.results     = ev.results
                st.session_state.ran_defense = True
                st.success("Analysis complete.")

    if st.session_state.ran_defense and st.session_state.evaluator:
        st.divider()
        st.header("Results")
        ev = st.session_state.evaluator
        df = ev.to_dataframe()
        show_results(ev, df)
        if st.button("Save Results"):
            ev.save("data/results/results.json")
            st.success("Saved.")


# ═══════════════════════════════════════════════════════════
# TAB 2 — Benchmark
# ═══════════════════════════════════════════════════════════
with tab2:
    st.header("Benchmark — Mixed Test Set")
    st.markdown(
        "Runs the blue team against a labeled dataset with both benign inputs and attacks, "
        "producing realistic F1 / Precision / Recall including true-negative count."
    )
    bench_v = st.selectbox("Blue Team Prompt Version", ["v1", "v2"], key="bench_v")

    if st.button("Run Benchmark", type="primary"):
        with open("data/test_cases.json", encoding="utf-8") as f:
            cases = json.load(f)
        ev   = Evaluator()
        blue = BlueTeamAgent(prompt_version=bench_v)
        bar  = st.progress(0)
        for i, case in enumerate(cases):
            label = "attack" if case["is_attack"] else "benign"
            with st.spinner(f"Case {i+1}/{len(cases)} ({label})..."):
                result = blue.analyze(case["text"])
                ev.add_result(case["text"], result, ground_truth=case["is_attack"])
            bar.progress((i+1) / len(cases))
        st.session_state["bench_ev"] = ev
        st.success("Benchmark complete.")

    if "bench_ev" in st.session_state:
        ev  = st.session_state["bench_ev"]
        df  = ev.to_dataframe()
        m   = ev.calculate_metrics()

        st.subheader("Metrics")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Accuracy",  f"{m['accuracy']:.1%}")
        c2.metric("Precision", f"{m['precision']:.1%}")
        c3.metric("Recall",    f"{m['recall']:.1%}")
        c4.metric("F1 Score",  f"{m['f1_score']:.1%}")
        c5.metric("Total",     m["total"])

        st.subheader("Confusion Matrix")
        cm_df = pd.DataFrame({
            "":              ["Predicted Attack", "Predicted Benign"],
            "Actual Attack": [m["tp"], m["fn"]],
            "Actual Benign": [m["fp"], m["tn"]],
        }).set_index("")
        st.dataframe(cm_df)

        show_results(ev, df)
        if st.button("Save Benchmark Results"):
            ev.save("data/results/benchmark_results.json")
            st.success("Saved.")


# ═══════════════════════════════════════════════════════════
# TAB 3 — Adaptive Attack
# ═══════════════════════════════════════════════════════════
with tab3:
    st.header("Adaptive Attack — Red Team Learns")
    st.markdown(
        "When an attack is detected with high confidence, the red team automatically "
        "generates a harder version. Track how detection rate changes across rounds."
    )

    adapt_sys    = st.text_area("Target system:", placeholder="e.g. A banking chatbot...", height=80, key="adapt_sys")
    adapt_rv     = st.selectbox("Red Team Prompt",  ["v1", "v2"], key="adapt_rv")
    adapt_bv     = st.selectbox("Blue Team Prompt", ["v1", "v2"], key="adapt_bv")
    adapt_rounds = st.slider("Adaptive rounds", 1, 3, 2)
    threshold    = st.slider("Confidence threshold to trigger adaptation", 0.5, 1.0, 0.7)

    if st.button("Run Adaptive Attack", type="primary"):
        if not adapt_sys.strip():
            st.warning("Please describe the target system.")
        else:
            red    = RedTeamAgent(prompt_version=adapt_rv)
            blue   = BlueTeamAgent(prompt_version=adapt_bv)
            pairs  = []

            with st.spinner("Generating initial attacks..."):
                initial = red.generate_attacks(adapt_sys, 3)

            for atk in initial:
                chain        = []
                current_text = atk["text"]

                for rnd in range(adapt_rounds + 1):
                    with st.spinner(f"Analyzing round {rnd}..."):
                        result = blue.analyze(current_text)

                    chain.append({
                        "round":       rnd,
                        "attack":      current_text,
                        "detected":    result.get("is_attack", False),
                        "confidence":  result.get("confidence", 0.0),
                        "severity":    result.get("severity", "none"),
                        "mitre":       result.get("mitre_technique_id", "none"),
                        "explanation": result.get("explanation", "")
                    })

                    if (result.get("is_attack") and
                            result.get("confidence", 0) >= threshold and
                            rnd < adapt_rounds):
                        with st.spinner(f"Red team adapting (round {rnd+1})..."):
                            current_text = red.generate_adaptive_attack(
                                current_text,
                                result.get("confidence", 0),
                                result.get("explanation", "")
                            )

                pairs.append(chain)

            st.session_state["adaptive_pairs"] = pairs
            st.success("Adaptive attack complete.")

    if st.session_state["adaptive_pairs"]:
        st.subheader("Detection Rate by Round")
        all_rounds = [step for chain in st.session_state["adaptive_pairs"] for step in chain]
        rdf        = pd.DataFrame(all_rounds)
        det_by_rnd = rdf.groupby("round")["detected"].mean().reset_index()
        det_by_rnd.columns = ["Round", "Detection Rate"]
        fig = px.line(det_by_rnd, x="Round", y="Detection Rate", markers=True,
                      title="Detection Rate vs. Adaptive Round", range_y=[0, 1.05])
        fig.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Attack Evolution Detail")
        for i, chain in enumerate(st.session_state["adaptive_pairs"], 1):
            with st.expander(f"Chain {i}"):
                for step in chain:
                    tag = "DETECTED" if step["detected"] else "EVADED"
                    st.markdown(f"Round {step['round']} — {tag} | confidence: {step['confidence']} | mitre: {step['mitre']}")
                    st.code(step["attack"], language="text")
                    st.caption(step["explanation"])
                    st.divider()

        if st.button("Save Adaptive Results"):
            os.makedirs("data/results", exist_ok=True)
            with open("data/results/adaptive_results.json", "w", encoding="utf-8") as f:
                json.dump(st.session_state["adaptive_pairs"], f, ensure_ascii=False, indent=2)
            st.success("Saved.")


# ═══════════════════════════════════════════════════════════
# TAB 4 — Live Target + Auto Report
# ═══════════════════════════════════════════════════════════
with tab4:
    st.header("Live Target Testing and Auto Defense Report")
    st.markdown(
        "Attack a real simulated enterprise system to measure actual data leakage. "
        "Then generate a full defense report with remediation recommendations automatically."
    )

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Step 1 — Select Target and Generate Attacks")
        scenario_map  = VictimLLM.scenario_list()
        scenario_key  = st.selectbox("Target Enterprise System", list(scenario_map.keys()),
                                     format_func=lambda k: scenario_map[k])
        live_num      = st.slider("Number of attacks", 3, 8, 5)
        live_red_v    = st.selectbox("Attack Strategy", ["v1", "v2", "world_aware"], key="live_red_v")

        preview_victim = VictimLLM(scenario=scenario_key)
        with st.expander("View Target System Prompt (sensitive data hidden)"):
            st.code(preview_victim.safe_system_prompt, language="text")

        if st.button("Generate and Launch Attacks", type="primary"):
            red    = RedTeamAgent(prompt_version="v2" if live_red_v != "world_aware" else "v2")
            victim = VictimLLM(scenario=scenario_key)
            blue   = BlueTeamAgent(prompt_version="v2")
            ev     = Evaluator()

            with st.spinner("Generating attacks..."):
                if live_red_v == "world_aware":
                    attacks = red.generate_world_aware_attacks(scenario_map[scenario_key])
                else:
                    attacks = red.generate_attacks(scenario_map[scenario_key], live_num)

            live_results = []
            bar          = st.progress(0)

            for i, atk in enumerate(attacks):
                with st.spinner(f"Attack {i+1}/{len(attacks)}: testing victim..."):
                    victim_result    = victim.respond(atk["text"])
                    detection_result = blue.analyze(atk["text"])
                    ev.add_result(atk["text"], detection_result, ground_truth=True)
                    live_results.append({
                        "attack":     atk["text"],
                        "victim":     victim_result,
                        "detection":  detection_result
                    })
                bar.progress((i+1) / len(attacks))

            st.session_state["live_ev"]      = ev
            st.session_state["live_results"] = live_results
            st.session_state["live_scenario"]= scenario_map[scenario_key]
            st.session_state["live_report"]  = None
            st.success("Attack session complete. See results on the right.")

    with col_right:
        st.subheader("Step 2 — Results and Report")

        if st.session_state.get("live_results"):
            results   = st.session_state["live_results"]
            ev        = st.session_state["live_ev"]
            m         = ev.calculate_metrics()
            breached  = sum(1 for r in results if r["victim"]["leaked"])
            total_atk = len(results)

            r1, r2, r3 = st.columns(3)
            r1.metric("Attacks Tested",     total_atk)
            r2.metric("Breaches",           breached)
            r3.metric("Breach Rate",        f"{breached/total_atk:.1%}" if total_atk > 0 else "0%")

            st.subheader("Attack-by-Attack Results")
            for i, r in enumerate(results, 1):
                v   = r["victim"]
                det = r["detection"]
                status = "BREACHED" if v["leaked"] else "defended"
                with st.expander(f"Attack {i} — {status} | severity: {v['severity']}"):
                    st.markdown("Attack Input:")
                    st.code(r["attack"], language="text")
                    st.markdown("Victim Response:")
                    st.code(v["response"], language="text")
                    if v["leaked"]:
                        st.warning(f"Data leaked: {', '.join(v['leaked_keywords'])}")
                    st.markdown(f"Blue Team: type={det.get('attack_type','?')} | "
                                f"confidence={det.get('confidence',0)} | "
                                f"mitre={det.get('mitre_technique_id','none')}")

            st.divider()
            st.subheader("Step 3 — Generate Defense Report")

            if st.button("Generate Auto Defense Report", type="primary"):
                reporter = DefenseReporter()
                with st.spinner("Gemini is writing the security report..."):
                    detection_results = [r["detection"] for r in results]
                    victim_results    = [r["victim"]    for r in results]
                    report = reporter.generate(
                        target_system    = st.session_state["live_scenario"],
                        detection_results= detection_results,
                        victim_results   = victim_results
                    )
                st.session_state["live_report"] = report
                st.success("Report generated.")

            if st.session_state.get("live_report"):
                report = st.session_state["live_report"]
                st.subheader("Security Assessment Report")
                st.text_area("Full Report", report["full_report"], height=500)

                if st.button("Save Report to File"):
                    reporter = DefenseReporter()
                    path     = reporter.save(report)
                    st.success(f"Saved to {path}")
