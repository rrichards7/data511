import streamlit as st
from utils.data_loader import load_player_data_from_api, load_gameweek_data_from_github
from utils.team_selection import adjust_selected_players, select_players_for_position
from utils.team_computation import get_top_players_by_position, adjust_team_to_budget
from visualizations import (
    draw_soccer_field,
    plot_total_points_comparison,
    plot_team_radar_chart,
    plot_cost_breakdown_by_position,
    total_points_vs_cost_yearly,
    ownership_vs_points_bubble_chart_with_dropdown
)
from utils.constants import FORMATION_MAP, BUDGET, COLOR_PALETTE, SECTION_ICONS, POSITION_FULL_NAMES
import pandas as pd

players_pred_df = pd.read_csv("data/predicted_df.csv")

def get_player_pred(name, team):
    try:
        name_clean = name.strip().split(".")[-1]
        x = players_pred_df[players_pred_df.web_name.str.contains(name_clean)][players_pred_df.team == team]
        return int(x.sort_values(['gw'], ascending=False).pred_points_rounded.iloc[0])
    except:
        return 0

st.markdown(
    f"<h2 style='text-align: center; color: {COLOR_PALETTE['App Title']};'>{SECTION_ICONS['App Title']} Ultimate FPL Manager<br> GW {load_gameweek_data_from_github('2024-25').GW.max() + 1}</h1>",
    unsafe_allow_html=True
)

player_data = load_player_data_from_api()
if player_data.empty:
    st.stop()

# Initialize session state
if 'selected_players' not in st.session_state:
    st.session_state.selected_players = {pos: [] for pos in ['GKP', 'DEF', 'MID', 'FWD']}
if 'best_team' not in st.session_state:
    st.session_state.best_team = None
if 'formation' not in st.session_state:
    st.session_state.formation = None

st.sidebar.markdown(
    f"<h3 style='color: {COLOR_PALETTE['Sidebar Pick']};'>{SECTION_ICONS['Pick Players']} Build Your Dream Team</h3>",
    unsafe_allow_html=True
)

formation = st.sidebar.selectbox("Choose Your Formation", list(FORMATION_MAP.keys()), index=0)
position_counts = FORMATION_MAP[formation]

formation_changed = (formation != st.session_state.formation)
st.session_state.formation = formation

# If formation changed, ensure selected players match new formation limits
if formation_changed:
    adjust_selected_players(position_counts, player_data)
    st.session_state.best_team = None  # Reset best team since formation changed

# Now select players for each position according to formation
selected_players = []
total_cost = 0
for position, count in position_counts.items():
    position_players = select_players_for_position(position, count, player_data)
    total_cost += sum(int(p['now_cost']) for p in position_players)
    selected_players.extend(position_players)

remaining_budget = BUDGET - total_cost
all_positions_complete = all(
    len(st.session_state.selected_players.get(position, [])) >= count
    for position, count in position_counts.items()
)

if not all_positions_complete:
    st.sidebar.error("Please ensure you have selected all required players for each position.")

if total_cost > BUDGET:
    st.sidebar.error("Budget exceeded!")

if st.session_state.best_team is None or formation_changed:
    best_team = get_top_players_by_position(player_data, formation)
    best_team = adjust_team_to_budget(best_team, BUDGET, player_data)
    st.session_state.best_team = best_team
else:
    best_team = st.session_state.best_team

col1, col2 = st.columns([2, 1])
with col1:
    team_to_display = st.radio("Select Team to View", ['Your Team', 'Best Team'])

    if team_to_display == 'Your Team':
        team_to_show = selected_players
    else:
        team_to_show = best_team

    if not team_to_show:
        st.write("**No players selected. Please select your team to view the field.**")
        field_fig = draw_soccer_field([], formation)
    else:
        field_fig = draw_soccer_field(team_to_show, formation)
    st.plotly_chart(field_fig, use_container_width=True)

with col2:
    user_total_cost = sum(p['now_cost'] for p in selected_players)
    best_total_cost = sum(p['now_cost'] for p in best_team)
    user_xp_next_gw = sum(get_player_pred(p['web_name'], p['team_name']) for p in selected_players)
    best_xp_next_gw = sum(get_player_pred(p['web_name'], p['team_name']) for p in best_team)

    st.markdown(
        f"<h3 style='color: {COLOR_PALETTE['Sidebar Budget']};'>{SECTION_ICONS['Budget Overview']} Budget Overview</h3>",
        unsafe_allow_html=True
    )
    st.write(f"**Your Team Cost:** £{user_total_cost / 10:.1f}m / £{BUDGET / 10:.1f}m")
    st.write(f"**Best Team Cost:** £{best_total_cost / 10:.1f}m / £{BUDGET / 10:.1f}m")

    st.markdown(
        f"<h3 style='color: {COLOR_PALETTE['Predicted Points']};'>{SECTION_ICONS['Target']} Points Prediction</h3>",
        unsafe_allow_html=True
    )
    st.write(f"**Your Team Predicted Points next GW:** {user_xp_next_gw}")
    st.write(f"**Best Team Predicted Points next GW:** {best_xp_next_gw}")

    if user_total_cost > BUDGET:
        st.error("Your team's budget is exceeded!")

    if best_total_cost > BUDGET:
        st.warning("The best team exceeds the budget constraints.")

    st.markdown(
        f"<h4 style='color: {COLOR_PALETTE['Performance Analysis']};'>{SECTION_ICONS['Performance Analysis']} {team_to_display} Players</h4>",
        unsafe_allow_html=True
    )

    if team_to_show:
        positions_order = ['FWD', 'MID', 'DEF', 'GKP']
        for pos in positions_order:
            pos_players = [p for p in team_to_show if p['position'] == pos]
            if pos_players:
                cols = st.columns(len(pos_players))
                for idx, player in enumerate(pos_players):
                    with cols[idx]:
                        photo_url = player.get('photo_url', 'https://via.placeholder.com/100')
                        # Center-align photo and caption using HTML
                        st.markdown(
                            f"""
                            <div style="text-align: center;">
                                <img src="{photo_url}" style="width:80px; border-radius:40%;">
                                <p style="margin-top:5px;">{player['web_name']}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
    else:
        st.write("**Please select your team or best team to view players.**")

st.divider()

st.markdown(
    f"<h3 align='center' style='color: {COLOR_PALETTE['Performance Analysis']};'>{SECTION_ICONS['Performance Analysis']} Team & Player Performance, Cost, and Ownership Insights</h3>",
    unsafe_allow_html=True
)

tab1, tab2 = st.columns(2)

with tab1:
    plot_total_points_comparison(selected_players, best_team)

    st.divider()

    plot_team_radar_chart(selected_players, best_team)

with tab2:
    total_points_vs_cost_yearly(player_data, 500)
    st.divider()
    ownership_vs_points_bubble_chart_with_dropdown(player_data, min_ownership_pct=10.0)

st.divider()

plot_cost_breakdown_by_position(selected_players, best_team)

user_player_names = set(p['web_name'] for p in selected_players)
best_player_names = set(p['web_name'] for p in best_team)
common_players = user_player_names & best_player_names

if common_players:
    st.write(f"**{SECTION_ICONS['Shared Players']} Shared Players Spotlight:** {', '.join(common_players)}")
else:
    st.write("**No common players between your team and the best team.**")

st.divider()