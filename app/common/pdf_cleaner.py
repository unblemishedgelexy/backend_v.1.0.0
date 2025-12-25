import pikepdf

def clean_pdf(input_path, output_path):
    with pikepdf.open(input_path) as pdf:
        pdf.remove_unreferenced_resources()
        pdf.save(output_path, optimize_streams=True)

    return output_path
