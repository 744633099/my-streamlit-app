import streamlit as st
import pandas as pd
import numpy as np
import re
import io

st.set_page_config(page_title="多机型自由对比", layout="wide")
st.title("多机型载荷数据自由对比工具")


# ==========================================
# 辅助函数
# ==========================================
def clean_num(val):
    if pd.isna(val): return np.nan
    match = re.search(r'[-+]?\d*\.?\d+', str(val))
    if match: return abs(float(match.group()))
    return np.nan


def calc_diff(a, c):  # a 是分子，c 是分母
    if pd.notna(a) and pd.notna(c) and c != 0:
        return (a - c) / c * 100
    return np.nan


def get_val(df, row_num, col_letter):
    try:
        r_idx = row_num - 1
        c_idx = ord(col_letter.upper()) - ord('A')
        return clean_num(df.iloc[r_idx, c_idx])
    except:
        return np.nan


def get_str(df, row_num, col_letter):
    try:
        r_idx = row_num - 1
        c_idx = ord(col_letter.upper()) - ord('A')
        return str(df.iloc[r_idx, c_idx]).strip()
    except:
        return ""


def get_max_abs(df, start_row, end_row, val_col, case_col):
    max_v, max_c = np.nan, ""
    for r in range(start_row, end_row + 1):
        v = get_val(df, r, val_col)
        if pd.notna(v) and (pd.isna(max_v) or v > max_v):
            max_v = v
            max_c = get_str(df, r, case_col)
    return max_v, max_c


# ==========================================
# 提取逻辑
# ==========================================
def extract_extremes(df):
    res = {}
    if df is None: return res
    res['Blade_Mxy'] = get_max_abs(df, 9, 10, 'G', 'D')
    res['Blade_Mz'] = get_max_abs(df, 11, 12, 'H', 'D')
    res['Hub_Fix_Mx'] = get_max_abs(df, 8, 9, 'E', 'D')
    res['Hub_Fix_Myz'] = get_max_abs(df, 14, 15, 'H', 'D')
    res['Yaw_Bend_Mxy'] = get_max_abs(df, 16, 17, 'F', 'C')
    res['Yaw_Torque_Mz'] = get_max_abs(df, 18, 19, 'G', 'C')
    return res


def extract_fatigue_blade_yaw(df):
    res = {}
    if df is None: return res
    res['Blade_Mx'] = (get_val(df, 5, 'C'), get_val(df, 10, 'C'))
    res['Blade_My'] = (get_val(df, 5, 'D'), get_val(df, 10, 'D'))
    res['Yaw_Bend_My'] = (get_val(df, 34, 'P'), get_val(df, 39, 'P'))
    res['Yaw_Torque_Mz'] = (get_val(df, 34, 'R'), get_val(df, 39, 'R'))
    return res


def extract_fatigue_hub(df):
    res = {}
    if df is None: return res
    res['Hub_Cen_Mx'] = (get_val(df, 11, 'K'), get_val(df, 16, 'K'))
    res['Hub_Fix_My'] = (get_val(df, 11, 'L'), get_val(df, 16, 'L'))
    res['Hub_Fix_Mz'] = (get_val(df, 11, 'M'), get_val(df, 16, 'M'))
    res['Hub_Rot_My'] = (get_val(df, 27, 'L'), get_val(df, 32, 'L'))
    res['Hub_Rot_Mz'] = (get_val(df, 27, 'M'), get_val(df, 32, 'M'))
    return res


# ==========================================
# 1. 侧边栏：基础数据源管理
# ==========================================
if 'num_models' not in st.session_state:
    st.session_state.num_models = 2

st.sidebar.header("1. 数据源配置")
models_data = {}
model_names = []

for i in range(st.session_state.num_models):
    default_name = chr(65 + i) + "机型" if i < 26 else f"机型{i + 1}"
    st.sidebar.markdown(f"---")
    model_name = st.sidebar.text_input(f"机型 {i + 1} 名称", value=default_name, key=f"name_{i}")

    if model_name:
        model_names.append(model_name)
        f_blade = st.sidebar.file_uploader(f"{model_name} - 叶根", type=["xlsx"], key=f"blade_{i}")
        f_hub = st.sidebar.file_uploader(f"{model_name} - 轮毂", type=["xlsx"], key=f"hub_{i}")
        f_yaw = st.sidebar.file_uploader(f"{model_name} - 偏航", type=["xlsx"], key=f"yaw_{i}")

        models_data[model_name] = {"blade": f_blade, "hub": f_hub, "yaw": f_yaw}

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("添加机型"):
        st.session_state.num_models += 1
        st.rerun()
with col2:
    if st.button("减少机型") and st.session_state.num_models > 2:
        st.session_state.num_models -= 1
        st.rerun()

# ==========================================
# 2. 主界面：自由配置对比组合
# ==========================================
st.markdown("2. 自定义对比组合")
st.info("提示：您可以在这里随意添加组合。比如，您可以设置“B比A”、“C比A”、“A比B”等等，结果会直接生成在下方表格中。")

# 初始化组合列表
if 'combos' not in st.session_state:
    st.session_state.combos = [{"numerator": "B机型", "denominator": "A机型"}]

# 渲染现有的组合
for idx, combo in enumerate(st.session_state.combos):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        num_model = st.selectbox(f"分子 (对比项)", options=model_names, index=model_names.index(combo["numerator"]) if combo[
                                                                                                                      "numerator"] in model_names else 0,
                                 key=f"num_{idx}")
    with c2:
        den_model = st.selectbox(f"分母 (基准项)", options=model_names,
                                 index=model_names.index(combo["denominator"]) if combo[
                                                                                      "denominator"] in model_names else 0,
                                 key=f"den_{idx}")
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("删除", key=f"del_{idx}"):
            st.session_state.combos.pop(idx)
            st.rerun()

    # 更新状态
    st.session_state.combos[idx] = {"numerator": num_model, "denominator": den_model}

# 添加按钮
if st.button("添加对比组合"):
    st.session_state.combos.append({"numerator": model_names[0], "denominator": model_names[-1]})
    st.rerun()

# ==========================================
# 3. 提取与计算
# ==========================================
if st.button("开始提取并生成报告", type="primary"):
    if len(model_names) < 2:
        st.error("请至少配置两个机型。")
    else:
        ext_results = {name: {"叶根": {}, "轮毂": {}, "偏航": {}} for name in model_names}
        fat_results = {name: {"叶根": {}, "轮毂": {}, "偏航": {}} for name in model_names}

        with st.spinner("正在提取原始数据..."):
            for name, files in models_data.items():
                if files["blade"]:
                    try:
                        rE = extract_extremes(pd.read_excel(files["blade"], sheet_name=1, header=None))
                        ext_results[name]["叶根"] = {k: v for k, v in rE.items() if 'Blade' in k}
                        rF = extract_fatigue_blade_yaw(pd.read_excel(files["blade"], sheet_name=3, header=None))
                        fat_results[name]["叶根"] = {k: v for k, v in rF.items() if 'Blade' in k}
                    except:
                        pass
                if files["hub"]:
                    try:
                        rE = extract_extremes(pd.read_excel(files["hub"], sheet_name=1, header=None))
                        ext_results[name]["轮毂"] = {k: v for k, v in rE.items() if 'Hub' in k}
                        rF = extract_fatigue_hub(pd.read_excel(files["hub"], sheet_name=2, header=None))
                        fat_results[name]["轮毂"] = rF
                    except:
                        pass
                if files["yaw"]:
                    try:
                        rE = extract_extremes(pd.read_excel(files["yaw"], sheet_name=2, header=None))
                        ext_results[name]["偏航"] = {k: v for k, v in rE.items() if 'Yaw' in k}
                        rF = extract_fatigue_blade_yaw(pd.read_excel(files["yaw"], sheet_name=3, header=None))
                        fat_results[name]["偏航"] = {k: v for k, v in rF.items() if 'Yaw' in k}
                    except:
                        pass


        # ==========================================
        # 4. 组装动态表格
        # ==========================================
        def build_table(results_dict, is_fatigue=False):
            rows = []
            # 映射名称
            if not is_fatigue:
                mod_map = {
                    "叶根": {'Blade_Mxy': '叶根Mxy', 'Blade_Mz': '叶根Mz'},
                    "轮毂": {'Hub_Fix_Mx': '轮毂固定Mx', 'Hub_Fix_Myz': '轮毂固定Myz'},
                    "偏航": {'Yaw_Bend_Mxy': '偏航弯矩Mxy', 'Yaw_Torque_Mz': '偏航扭矩Mz'}
                }
            else:
                mod_map = {
                    "叶根": {'Blade_Mx': '叶根Mx', 'Blade_My': '叶根My'},
                    "轮毂": {'Hub_Cen_Mx': '轮毂中心Mx', 'Hub_Fix_My': '轮毂中心固定My', 'Hub_Fix_Mz': '轮毂中心固定Mz',
                           'Hub_Rot_My': '轮毂中心旋转My', 'Hub_Rot_Mz': '轮毂中心旋转Mz'},
                    "偏航": {'Yaw_Bend_My': '偏航弯矩My', 'Yaw_Torque_Mz': '偏航扭矩Mz'}
                }

            for mod in ["叶根", "轮毂", "偏航"]:
                for key, disp_name in mod_map[mod].items():
                    row = {"通道": disp_name}
                    has_data = False

                    # 针对每个用户配置的组合生成列
                    for combo in st.session_state.combos:
                        num_m = combo["numerator"]
                        den_m = combo["denominator"]

                        if not is_fatigue:
                            # 极限处理
                            n_val, n_case = results_dict[num_m][mod].get(key, (np.nan, ""))
                            d_val, d_case = results_dict[den_m][mod].get(key, (np.nan, ""))

                            if pd.notna(n_val) or pd.notna(d_val): has_data = True

                            # 列名格式： 分子载荷 / 分母载荷 / 差异
                            row[f"[分子]{num_m}载荷"] = n_val
                            row[f"[分母]{den_m}载荷"] = d_val
                            row[f"差异({num_m}比{den_m})%"] = calc_diff(n_val, d_val)
                        else:
                            # 疲劳处理
                            n_m4, n_m9 = results_dict[num_m][mod].get(key, (np.nan, np.nan))
                            d_m4, d_m9 = results_dict[den_m][mod].get(key, (np.nan, np.nan))

                            if pd.notna(n_m4) or pd.notna(d_m4) or pd.notna(n_m9) or pd.notna(d_m9): has_data = True

                            row[f"[分子]{num_m}_m4"] = n_m4
                            row[f"[分母]{den_m}_m4"] = d_m4
                            row[f"差异({num_m}比{den_m})_m4%"] = calc_diff(n_m4, d_m4)

                            row[f"[分子]{num_m}_m9"] = n_m9
                            row[f"[分母]{den_m}_m9"] = d_m9
                            row[f"差异({num_m}比{den_m})_m9%"] = calc_diff(n_m9, d_m9)

                    if has_data:
                        rows.append(row)
            return pd.DataFrame(rows)


        # 生成极限表
        st.subheader("极限数据对比")
        df_ext = build_table(ext_results, is_fatigue=False)
        if not df_ext.empty:
            st.dataframe(df_ext.style.format(precision=2), use_container_width=True)
        else:
            st.info("无极限数据。")

        # 生成疲劳表
        st.subheader("疲劳数据对比")
        df_fat = build_table(fat_results, is_fatigue=True)
        if not df_fat.empty:
            st.dataframe(df_fat.style.format(precision=2), use_container_width=True)
        else:
            st.info("无疲劳数据。")

        # 导出
        if not df_ext.empty or not df_fat.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if not df_ext.empty: df_ext.to_excel(writer, sheet_name='极限', index=False)
                if not df_fat.empty: df_fat.to_excel(writer, sheet_name='疲劳', index=False)

            st.download_button(
                label="下载对比结果 Excel",
                data=output.getvalue(),
                file_name="自由组合对比结果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )