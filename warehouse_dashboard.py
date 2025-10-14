    
    if not filtered_df.empty:
        # Calculate alerts
        zero_stock_count = len(filtered_df[filtered_df["QTYAVAILABLE"] == 0])
        low_stock_df = filtered_df[filtered_df["QTYAVAILABLE"] < threshold].copy()
        
        # Zero-stock badge
        col1, col2 = st.columns([1, 4])
        with col1:
            if zero_stock_count > 0:
                st.error(f"🚨 {zero_stock_count} items with **zero** available stock!")
            else:
                st.success("✅ No zero-stock items detected.")
        
        with col2:
            st.info(f"Low stock items (QTYAVAILABLE < {threshold}): **{len(low_stock_df)}**")
        
        # Low-stock table with conditional formatting
        if not low_stock_df.empty:
            st.subheader("Low Stock Items")
            
            def highlight_stock(val):
                if val == 0:
                    return "background-color: #ffcccc; color: #d32f2f; font-weight: bold"  # Red for zero
                elif val < threshold:
                    return "background-color: #fff3cd; color: #f57c00"  # Yellow for low
                return ""
            
            # Apply styling to QTYAVAILABLE column
            styled_df = low_stock_df[["SKU", "DESCR", "QTYAVAILABLE", "WAREHOUSEGROUP"]].style.applymap(
                highlight_stock, subset=["QTYAVAILABLE"]
            )
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=300,
                hide_index=True,
                column_config={
                    "QTYAVAILABLE": st.column_config.NumberColumn("Available Quantity", format="%.0f"),
                }
            )
        else:
            st.info(f"✅ No low-stock items based on threshold ({threshold}) and current filters.")
    else:
        st.warning("No data to display. Adjust filters in the sidebar.")
# Footer
st.markdown("---")
st.markdown("Built with Streamlit & Plotly. For issues, check console or file format.")