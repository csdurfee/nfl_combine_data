import altair as alt
import get_combine_data


def relative_peformance(all_data):
    step = 40
    overlap = 0

    DEFAULT_POSITION = "RB"

    alt.data_transformers.disable_max_rows()

    eav = get_combine_data.quantiles_as_eav(all_data, position_key='general_position')

    len(eav.dropna())

    DROPDOWN_POSITIONS = list(eav.position.unique())

    input_dropdown = alt.binding_select(options=DROPDOWN_POSITIONS, name='position')

    position_selection = alt.selection_single(fields=['position'], bind=input_dropdown, init={"position": "Running Back"})

    c = alt.Chart(eav, height=step
    ).add_selection(
        position_selection
    ).transform_filter(
        position_selection
    ).transform_joinaggregate(
        mean_value='mean(result)', groupby=['event']
    ).transform_bin(
        ['bin_min', 'bin_max'], "result", bin=alt.Bin(maxbins=100)
    ).transform_aggregate(
        value='count()', groupby=['event', 'mean_value', 'bin_min', 'bin_max']
    ).transform_impute(
        impute='value', groupby=['event', 'mean_value'], key='bin_min', value=0
    ).mark_area(

    ).encode(
        alt.X('bin_min:Q', scale=alt.Scale(domain=[0,100]), title=None),
        alt.Y(
            'value:Q',
            scale=alt.Scale(range=[step, -step * overlap]),
            axis=None
        ),
        alt.Fill(
            'mean_value:Q',
            #legend=None,
            scale=alt.Scale(domain=[20, 80], scheme='redyellowblue', reverse=True),
            title='mean percentile'
        ),
        alt.Row('event:N', title=None, header=alt.Header(labelAngle=0, labelAlign='left')),
        tooltip=alt.Tooltip(['mean_value:Q'], format=".2", title='mean percentile')
    )
    c.properties(
        title='Percentile performance vs. all drafted players',
        bounds='flush'
    ).configure_view(
        stroke=None
    ).configure_title(
        anchor='middle',
        align='center'
    )
    return c