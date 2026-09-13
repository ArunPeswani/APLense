# --- CLEAN FLUID HEATMAP ---
        st.subheader(f"Visual Heatmap ({run_label})")
        st.write("💡 *Tip: Use Plotly's built-in box zoom or pan tool on the top right toolbar to inspect specific clusters closely.*")
        
        text_annotations = [[f"{val:.1f}%" for val in row] for row in similarity_matrix]
        
        fig = go.Figure(data=go.Heatmap(
            z=similarity_matrix,
            x=filenames,
            y=filenames,
            text=text_annotations,
            texttemplate=None,  # Keep cell text hidden for 99+ files to prevent clutter; values show on hover!
            colorscale="Reds" if "Paraphrase" not in run_label else "Oranges",
            zmin=0,
            zmax=100
        ))
        fig.update_layout(
            height=650,  # Clean fixed viewport height with native scrolling/panning
            margin=dict(l=150, r=50, t=50, b=150),
            xaxis=dict(tickangle=-45),
            yaxis=dict(autorange='reversed')
        )
        
        st.plotly_chart(fig, use_container_width=True)
