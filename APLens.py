# --- SCROLLABLE MATPLOTLIB/SEABORN HEATMAP ---
        st.subheader(f"Visual Heatmap ({run_label})")
        st.write("💡 *Tip: High-resolution heatmap generated below. You can right-click to save or zoom the image.*")
        
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Dynamically size figure based on number of files (e.g., 0.3 inches per file)
        fig_size = max(8, total_files * 0.25)
        fig, ax = plt.subplots(figsize=(fig_size, fig_size))
        
        sns.heatmap(
            df, 
            annot=total_files <= 15,  # Only show numbers inside cells if file count is manageable, to avoid clutter
            fmt=".1f", 
            cmap="Reds" if "Paraphrase" not in run_label else "YlOrRd", 
            cbar=True, 
            square=True,
            linewidths=.5,
            ax=ax,
            vmin=0,
            vmax=100
        )
        plt.xticks(rotation=45, ha='right', fontsize=9)
        plt.yticks(fontsize=9)
        plt.title(f"Similarity Matrix Heatmap - {run_label}", fontsize=14, pad=20)
        
        # Display natively in Streamlit inside a scrollable container
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
