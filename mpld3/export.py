import matplotlib
import uuid
from functools import partial
matplotlib.use('Agg')  # don't display plots
import matplotlib.pyplot as plt
import subprocess
import mpld3
import multiprocessing
from visualize_tests import ExecFile
import os
import diffimg

HTML_TEMPLATE = """
<html>
<head>

<style type="text/css">
.fig {{
  height: 500px;
}}
{extra_css}
</style>
</head>

<body>
<div id="wrap">
    <div class="figures">
        {figures}
    </div>
</div>
<script>
    var draw_figures = function(){{
        var commands = [{js_commands}];
        for (i = 0; i < commands.length; i++) {{
            commands[i](mpld3);
        }}
    }}
    draw_figures()
</script>
</body>
</html>
"""

MPLD3_TEMPLATE = """
<div class="fig" id="fig{figid:03d}"></div>
"""

JS_TEMPLATE = """
function(mpld3){{
  {extra_js}
  mpld3.draw_figure("fig{figid:03d}", {figure_json});
}},
"""

def identical_images_test(image_path_1, image_path_2):
    percentage_diff = diffimg.diff(image_path_1, image_path_2, delete_diff_file=True)
    return True if percentage_diff == 0 else False

def snapshot_mpld3_plot(plot_filename, output_file_path=None, output_folder=mpld3.D3_SNAPSHOT_PATH):
    assert output_file_path or output_folder, "output_file_path or output_folder is required"
    result = ExecFile(plot_filename)
    figures = {} 
    html_fig_id_format = "fig{fig_id:03d}"
    html_fig_ids = []
    for fig_id, (fig, extra_js, extra_css) in enumerate(result.iter_json()):
        figures.setdefault("js", []).append(JS_TEMPLATE.format(
                figid=fig_id, 
                figure_json=fig,
                extra_js=extra_js
            )
        )
        figures.setdefault("html", []).append(
            MPLD3_TEMPLATE.format(figid=fig_id)
        )
        html_fig_ids.append(html_fig_id_format.format(fig_id=fig_id))

    if not figures.get("html"):
        return
    figures_html = "".join(figures.get("html"))
    js_script = "".join(figures.get("js"))

    rendered = HTML_TEMPLATE.format(
        figures=figures_html,
        js_commands=js_script,
        extra_css=""
    )
    
    output_html_path = os.path.join(output_folder, "temp/", "_snapshot_{id}.html".format(id=uuid.uuid4().hex))
    with open(output_html_path, 'w+') as f:
        f.write(rendered)

    if not output_file_path:
        export_filename = ".".join(plot_filename.split("/")[-1].split(".")[0:-1])+".jpeg"
        output_file_path = os.path.join(output_folder, export_filename) 

    command = [
        mpld3.SCREENSHOT_BIN, 
        output_html_path,
        output_file_path,
        mpld3.urls.D3_LOCAL,
        mpld3.urls.MPLD3_LOCAL,
    ]
    subprocess.call(command)
    os.remove(output_html_path) if os.path.exists(output_html_path) else None
    return output_file_path

def snapshot_multiple_mpld3_plots(plot_filenames, output_folder=mpld3.D3_SNAPSHOT_PATH):
    pool = multiprocessing.Pool(multiprocessing.cpu_count()) 
    pool.map(partial(snapshot_mpld3_plot, **{
        "output_folder": output_folder
    }), plot_filenames)
