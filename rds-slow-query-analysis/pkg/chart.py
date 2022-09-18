from matplotlib import pyplot


def plot_bar_chart(title, yaxis_label, xaxis_label, yaxis, xaxis, colors, output_file):
    print(f"initiating chart creation at {output_file}")
    pyplot.bar(xaxis, yaxis, color=colors)
    pyplot.title(title, fontsize=14)
    pyplot.xlabel(xaxis_label, fontsize=14)
    pyplot.ylabel(yaxis_label, fontsize=14)
    pyplot.grid(True)
    pyplot.savefig(output_file, bbox_inches='tight')
    pyplot.close()
    print(f"successfully generated chart at {output_file}")
