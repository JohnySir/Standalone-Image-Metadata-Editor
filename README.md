# **🖼️ Standalone Image Metadata Editor**

A simple, user-friendly Python application built with **Gradio** and **Pillow** to view, edit, and manage Stable Diffusion and custom metadata inside image files (primarily PNG).

This application allows you to:

* **Upload** ⬆️ an image (PNG recommended).  
* **View** all embedded metadata (including parameters for AI images).  
* **Edit** common fields like **Prompt**, **Steps**, **Seed**, and **CFG Scale**.  
* **Add/Edit** custom key/value pairs.  
* **Save** 💾 a new PNG copy with updated metadata.  
* **Clear** 🗑️ all existing metadata.

![Image Metadata Editor in Forge](assets/ui.png)

## **🚀 Quick Start**

1. **Install Requirements** (You need Python, Gradio, and Pillow):  
   `pip install gradio Pillow`

2. **Run the Script**:  
   `standalone_metadata_editor.py`

## **💡 Inspiration**

This standalone tool was created based on the excellent work of the **Image Metadata Editor Forge** extension:

* **Original Extension:** [MackinationsAi/sd-forge-metadata-editor](https://github.com/MackinationsAi/sd-forge-metadata-editor)

**Note:** This script removes all dependencies on the Stable Diffusion WebUI environment to run completely on its own.
