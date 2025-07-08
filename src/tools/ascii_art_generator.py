def ascii_art_generator(data):
    import numpy as np
    import matplotlib.pyplot as plt
    from io import BytesIO

    # Convert the data string into an array of numbers
    values = list(map(float, data.split(',')))
    labels = [str(i) for i in range(len(values))]

    # Create a simple horizontal bar graph
    plt.barh(labels, values)
    plt.xlabel('Value')
    plt.title('ASCII Art Graph')

    # Save the plot to a bytes buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='svg')
    buffer.seek(0)

    # Convert the SVG to ASCII art (a simplified representation)
    # Note: This is just a placeholder for actual ASCII conversion logic
    ascii_art = """\n" + "\n".join([f"{label}: {value}" for label, value in zip(labels, values)]) + "\n"""

    plt.close()  # Close the plot to free up memory
    return ascii_art