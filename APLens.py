# --- NATIVE SCROLLABLE HEATMAP ---
        st.subheader(f"Visual Heatmap ({run_label})")
        st.write("💡 *Tip: Use the chart toolbar on the top right to zoom, pan, or download the high-resolution matrix view.*")
        
        text_annotations = [[f"{val:.1f}%" for val in row] for row in similarity_matrix]
        
        # Dynamically scale chart size based on number of files (~22px per file)
        chart_dimension = max(700, total_files * 22)
        
        fig = go.Figure(data=go.Heatmap(
            z=similarity_matrix,
            x=filenames,
            y=filenames,
            text=text_annotations,
            texttemplate="%{text}",
            colorscale="Reds" if "Paraphrase" not in run_label else "Oranges",
            zmin=0,
            zmax=100
        ))
        fig.update_layout(
            width=chart_dimension,
            height=chart_dimension,
            margin=dict(l=150, r=50, t=50, b=150),
            xaxis=dict(tickangle=-45)
        )
        
        # Render natively using Streamlit's built-in chart wrapper (False allows custom width/height scrolling)
        st.plotly_chart(fig, use_container_width=False)
