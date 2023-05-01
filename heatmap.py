import get_combine_data
import altair as alt

def get_heatmap(draft_pos_corr):
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
        title="Influence of combine results on draft position (r^2)"
    )

    return chart + text
