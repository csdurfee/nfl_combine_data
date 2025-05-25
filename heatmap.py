import get_combine_data
import altair as alt

def get_heatmap(draft_pos_corr, extra_title = ""):
    chart = alt.Chart(draft_pos_corr)

    scale = alt.Scale(scheme='redyellowblue', reverse=True)

    chart = chart.mark_rect().encode(
        alt.X('Rank:O', axis=alt.Axis(orient='top', labelAngle=0)),
        y='Position:O',
        color=alt.Color('Importance:Q', scale=scale),
        tooltip=alt.Tooltip('Importance:O', format=".3")
    )

    text = chart.mark_text(baseline='middle', fontSize=14).encode(
        alt.Text('Event:O'),
        color=alt.value("black")
    )

    chart = chart.properties(
        width=600, height=600
    ).properties(
        title="Correlation between combine results and draft position (r^2)" + extra_title
    )

    return chart + text
