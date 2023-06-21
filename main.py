from flask import Flask, request, render_template, jsonify, url_for, send_file
import pandas as pd
import subprocess
import os
import io
import tempfile
import plotly.express as px
import plotly.io as pio
from award import main


app = Flask(__name__)

@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        quarter = int(request.form["quarter"])  # Get the selected quarter from the form
        year = request.form.get('year')
        action = request.form.get('action')
        print(action)
        
        try:
            df_data = process_quarter(quarter, year)
            if action == 'download':
                fname = f"quarterly_{quarter}_report.csv"
                fname = download_csv(df_data, fname)
                return jsonify({'success': True, 'filename': fname, 'action': 'download'})
            elif action == 'plot':
                return bonus_chart(quarter,year)

        except AttributeError:
            return jsonify({'error': "No data present for this quarter or year yet"})
        except Exception as e:
            return jsonify({'error': f"An error occurred: {e}"})
    else:
        return render_template("index.html")

@app.route("/download/<filename>")
def download_file(filename):
    try:
        return send_file(os.path.join('static', filename), as_attachment=True, mimetype='text/csv')
    except Exception as e:
        return str(e)

@app.route("/delete/<filename>", methods=['POST'])
def delete_file(filename):
    file_path = os.path.join('static', filename)
    try:
        os.remove(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})



@app.route("/bonus_plot/<quarter>/<year>", methods=["GET"])
def bonus_plot(quarter, year):
    df = process_quarter(quarter, year)

    
    # Sort the dataframe by 'Total Bonus'
    df = df.sort_values('Total Bonus')
    
    fig = px.bar(df, 
                 x='Driver ID', 
                 y='Total Bonus', 
                 color='Total Bonus',   # change the color to be based on 'Total Bonus'
                 title='Total Bonus per Driver',
                 hover_data=['Total Bonus'],   # this will add a hover text for 'Total Bonus'
                 labels={'Total Bonus':'Total Bonus', 'Driver ID':'Driver ID'})

    # Convert the figures to HTML and remove the surrounding <html> tags
    plot_html = pio.to_html(fig, full_html=False)
    
    return render_template('plot.html', plot=plot_html)

@app.route("/bonus_chart/<quarter>/<year>/<driver_id>", methods=["GET"])
def bonus_chart(quarter, year, driver_id):
    df = process_quarter(quarter, year)
    # Sort the dataframe by 'Total Bonus'
    df = df.sort_values('Total Bonus')
    # print(df.to_json(orient='records'))
    # Send DataFrame as JSON to the client
    return render_template('chart.html', data=df.to_json(orient='records'), driverId=driver_id)





def process_quarter(quarter: int, year: int):
    """Process the file and delete it afterwards."""
    return main(int(quarter), int(year))

# def download_csv(df: pd.DataFrame, fname:str):
#     temp = tempfile.NamedTemporaryFile(suffix=".csv")
#     df.to_csv(temp.name, index=False)
#     return send_file(temp.name, as_attachment=True, attachment_filename=fname)
def download_csv(df: pd.DataFrame, fname:str):
    if not os.path.isdir('static'):
        os.makedirs('static')
    file_path = os.path.join('static', fname)
    df.to_csv(file_path, index=False)
    return fname


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)