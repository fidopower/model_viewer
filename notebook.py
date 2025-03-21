import marimo

__generated_with = "0.11.23-dev5"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    file = mo.ui.file(label="GridLAB-D model",filetypes=[".json"])
    file
    return (file,)


@app.cell
def _(file, json, mo):
    # Model check
    def error(msg):
        return mo.md(f"**<font color=red>ERROR: {msg}</font>**")

    def exception(msg):
        return mo.md(f"**<font color=red style=\"background-color:yellow\">EXCEPTION: {msg}</font>**")

    def info(msg):
        return mo.md(f"**<font color=blue>INFO: {msg}</font>**")

    mo.stop(not file.value,info("no file uploaded"))
    try:
        model = json.loads(file.contents(0))
    except Exception as err:
        mo.stop(True,exception(err))
    mo.stop("application" not in model,error("not a valid JSON model (no 'application' tag)"))
    mo.stop(model["application"]!="gridlabd",error("not a valid GridLAB-D model ('application' is not 'gridlabd')"))
    return error, exception, info, model


@app.cell
def _(file, mo, model):
    N = {
        "modules" : len(model["modules"]),
        "modules_used": len(set([x["module"] for x in model["classes"].values()])),
        "classes" : len(model["classes"]),
        "classes_used": len(set([x["class"] for x in model["objects"].values()])),
        "objects" : len(model["objects"]),
    }
    mo.md(f"**{file.name(0)}**: {N['modules_used']} modules used of {N['modules']} loaded, {N['classes_used']} classes used of {N['classes']} defined, {N['objects']} objects.")
    return (N,)


@app.cell
def _(mo, pd):
    viewer_ui = mo.ui.dropdown(options={"Static dataframe": lambda x:pd.DataFrame(x).transpose(),
                                        "Interactive dataframe": lambda x: mo.ui.dataframe(pd.DataFrame(x).transpose(),page_size=10),
                                        "Data explorer": lambda x: mo.ui.data_explorer(pd.DataFrame(x).transpose())
                                       },
                               label="View data as",
                               value = "Static dataframe",
                              )
    header_ui = mo.ui.checkbox(label="Show header data")
    class_ui = mo.ui.checkbox(label="Show all classes")

    return class_ui, header_ui, viewer_ui


@app.cell
def _(model, objects_ui):
    object_columns = [x for x,y in model['classes'][objects_ui.value].items() if isinstance(y,dict)]
    return (object_columns,)


@app.cell
def _(mo, model, os, pd):
    _files = {}
    _reader = {
        ".csv" : lambda x: pd.read_csv(x,parse_dates=True),
        ".json" : lambda x: pd.read_json(x,parse_dates=True),
    }
    for _list in [[y for y in x.values() if os.path.exists(y)] for x in model["objects"].values()]:
        for _file in _list:
            try:
                _reader = _reader[os.path.splitext(_file)[1]]
            except:
                _reader = lambda x: open(x).read()
            _files[_file] = _reader(_file)
    files_ui = mo.ui.tabs(_files) if _files else mo.md("No files found")
    return (files_ui,)


@app.cell
def _(mo, model):
    _classes = set([x["class"] for x in model['objects'].values() if "latitude" in x and "longitude" in x])
    _columns = []
    for _class in _classes:
        _columns.extend([x for x,y in model["classes"][_class].items() if isinstance(y,dict)])
    column_ui = mo.ui.multiselect(label="Hover data",options=sorted(_columns),value=[])
    # cluster_ui = mo.ui.checkbox(label="Cluster nodes")
    return (column_ui,)


@app.cell
def _(model, pd):
    geodata = pd.DataFrame({x:y for x,y in model["objects"].items() if "latitude" in y and "longitude" in y}).transpose()
    geodata = geodata.astype({"latitude":float,"longitude":float})
    return (geodata,)


@app.cell
def _(class_ui, header_ui, model, viewer_ui):
    used_classes = sorted(set([y["class"] for x,y in model["objects"].items()]))
    hide_columns = model["header"].keys() if not header_ui.value else []
    # hide_columns.extend([x for x in object_columns if x not in column_ui.value])
    objects = {
        x: viewer_ui.value(
            {y: {u:v for u,v in z.items() if u not in hide_columns} for y, z in model["objects"].items() if z["class"] == x}
        )
        # for x in set([x["class"] for x in model["objects"].values()])
        for x in (sorted(model["classes"]) if class_ui.value else used_classes)
    }
    return hide_columns, objects, used_classes


@app.cell
def _(class_ui, mo, model, pd, used_classes):
    classes = {
        x: mo.ui.tabs(
            {
                y: pd.DataFrame(
                    {
                        u: {
                            t: (
                                w if not isinstance(w, dict) else "|".join(w)
                            ).replace("|", "\n")
                            for t, w in v.items()
                        }
                        for u, v in z.items()
                        if isinstance(v, dict)
                    }
                ).transpose()
                for y, z in sorted(model["classes"].items())
                if z["module"] == x and y in (model["classes"] if class_ui.value else used_classes)
            }
        )
        for x in sorted(set([x["module"] for x in model["classes"].values()]))
    }
    return (classes,)


@app.cell
def _(classes, mo):
    classes_ui = mo.ui.tabs(classes)
    return (classes_ui,)


@app.cell
def _(mo, objects):
    objects_ui = mo.ui.tabs(objects)
    return (objects_ui,)


@app.cell
def _(column_ui, geodata, model, np, pd, px):
    _busses = {x: y for x, y in model["objects"].items() if y["class"] == "bus"}
    _branches = {
        x: y for x, y in model["objects"].items() if y["class"] == "branch"
    }
    _lines = [
        [
            [
                _busses[y["from"]]["longitude"],
                _busses[y["to"]]["longitude"],
                float("nan"),
            ],
            [
                _busses[y["from"]]["latitude"],
                _busses[y["to"]]["latitude"],
                float("nan"),
            ],
        ]
        for x, y in _branches.items()
        if y["from"] and y["to"]
    ]
    _data = pd.DataFrame(
        data={
            "longitude": np.array([x for x, y in _lines]).flatten(),
            "latitude": np.array([y for x, y in _lines]).flatten(),
        },
        dtype=float,
    )

    # lines
    map = px.line_map(
        data_frame=_data,
        lat="latitude",
        lon="longitude",
    )
    _hoverdata = {
        x: "<BR>".join([f"<B>{u}</B>: {v}" for u, v in y.items() if u in column_ui.value])
        for x, y in geodata.to_dict("index").items()
    }
    map.add_scattermap(
        below="",
        lat=geodata["latitude"],
        lon=geodata["longitude"],
        hoverinfo="text",
        hovertext=[f"<U>{x}</U><BR><BR>{y}..." for x,y in _hoverdata.items()],
        # hoverdata=column_ui.value,
    )
    _limits = (
        max(
            abs(geodata.latitude.max() - geodata.latitude.min()),
            geodata.longitude.max() - geodata.longitude.min(),
        )
        * 111
    )
    map.update_layout(
        map_zoom=11 - np.log(_limits),
        map_center={
            "lat": (geodata.latitude.max() + geodata.latitude.min()) / 2,
            "lon": (geodata.longitude.max() + geodata.longitude.min()) / 2,
        },
    )
    None
    return (map,)


@app.cell
def _(
    class_ui,
    classes_ui,
    column_ui,
    files_ui,
    header_ui,
    map,
    mo,
    objects_ui,
    viewer_ui,
):
    tabs_ui = mo.ui.tabs(
        {
            "Objects": mo.vstack(
                [
                    mo.hstack(
                        [viewer_ui, header_ui, class_ui],
                        justify="start",
                    ),
                    objects_ui,
                ]
            ),
            "Geodata": mo.vstack([mo.hstack([column_ui],justify='start'),map]),
            "Files" : files_ui,
            "Classes": classes_ui,
        },
        lazy=True,
    )
    tabs_ui
    return (tabs_ui,)


@app.cell
def _():
    import marimo as mo
    import os
    import json
    import pandas as pd
    import numpy as np
    import plotly.express as px
    return json, mo, np, os, pd, px


if __name__ == "__main__":
    app.run()
