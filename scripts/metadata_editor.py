import gradio as gr
import tempfile
import json

from io import BytesIO
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from modules import scripts, images
from modules.ui_common import plaintext_to_html


class ImageMetadataEditorForForge(scripts.Script):
    sorting_priority = 13
    
    def title(self):
        return "Image Metadata Editor"
    
    
    def show(self, is_img2img):
        return scripts.AlwaysVisible
    
    
    def ui(self, *args, **kwargs):
        css = """
            .wrap-code pre,
            .wrap-code code {
                white-space: pre-wrap !important;
                word-wrap: break-word !important;
                overflow-wrap: break-word !important;
            }
        """
        with gr.Blocks(css=css) as ui:
            with gr.Accordion(open=False, label=self.title()):
                gr.HTML("""<div style="margin-bottom: 10px;"><h3>Upload an image to view, add &/or edit its metadata. (Supports PNG [text chunks] & JPEG [EXIF] metadata editing).</p></div>""")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        input_image = gr.Image(label="Source", type="pil", interactive=True, height=512)

                        with gr.Column():
                            read_metadata_btn = gr.Button("Read Metadata", variant="secondary", size="sm", visible=False)
                            
                            clear_metadata_btn = gr.Button("Clear Metadata", variant="secondary", size="sm")
                            save_metadata_btn = gr.Button("Save w/ Metadata", variant="secondary", size="sm")

                    with gr.Column(scale=2):
                        with gr.Tab("Generation Info"):
                            with gr.Accordion(open=False, label="Extracted Metadata"):
                                info_html = gr.HTML(label="")

                            with gr.Group():
                                gr.HTML("<h4>Edit Parameters</h4>")

                                with gr.Row():
                                    prompt_text = gr.Textbox(label="Prompt", lines=3, max_lines=3, placeholder="Enter image generation prompt...", interactive=True, show_copy_button=True)
                                
                                with gr.Row():
                                    negative_prompt_text = gr.Textbox(label="Negative Prompt", lines=2, max_lines=2, placeholder="Enter negative prompt...", interactive=True, show_copy_button=True)

                                with gr.Row():
                                    steps = gr.Number(label="Steps", value=20, interactive=True, minimum=1, maximum=150)
                                    cfg_scale = gr.Number(label="CFG Scale", value=7.0, interactive=True, minimum=1.0, maximum=30.0)
                                    
                                with gr.Row():
                                    sampler = gr.Textbox(label="Sampler", interactive=True, placeholder="DPM++ 2M")
                                    scheduler = gr.Textbox(label="Scheduler", interactive=True, placeholder="Karras")
                                    
                                with gr.Row():
                                    model = gr.Textbox(label="baseModel", interactive=True, placeholder="Model name")
                                    seed = gr.Number(label="Seed", value=-1, interactive=True)
                                    
                                with gr.Row():
                                    width = gr.Number(label="Width", value=512, interactive=True, minimum=64, maximum=2048)
                                    height = gr.Number(label="Height", value=512, interactive=True, minimum=64, maximum=2048)
                        
                        with gr.Tab("Raw Metadata"):
                            metadata_json = gr.Code(label="Raw Metadata (JSON)", language="json", lines=24, interactive=True, elem_classes=["wrap-code"])
                            
                        with gr.Tab("Custom Fields"):
                            gr.HTML("<h4>Add Custom Metadata</h4>")
                            with gr.Row():
                                custom_key = gr.Textbox(label="Key", placeholder="metadata_key", scale=1)
                                custom_value = gr.Textbox(label="Value", placeholder="metadata_value", scale=2)
                                add_custom_btn = gr.Button("Add", size="sm", scale=0)

                            custom_fields_display = gr.Textbox(label="Custom Fields (JSON format)", lines=17, interactive=True, placeholder='{"key1": "value1", "key2": "value2"}', info="Edit this JSON directly to modify custom fields")

                        with gr.Tab("Output Image", visible=False):
                            output_image = gr.Image(label="Output Image with Metadata", type="pil", height=450)
                            download_file = gr.File(label="", type="file", visible=True, interactive=True)
                    
                status_display = gr.HTML()


        def parse_parameters_string(parameters_str):
            if not parameters_str:
                return {}, "", ""
            
            lines = [line.strip() for line in parameters_str.split('\n') if line.strip()]
            if not lines:
                return {}, "", ""

            prompt = lines[0]
            negative_prompt = ""

            for i, line in enumerate(lines[1:], 1):
                if line.startswith('Negative prompt:'):
                    negative_prompt = line.replace('Negative prompt:', '').strip()
                    break

            params = {}
            if len(lines) > 1:
                for line in reversed(lines):
                    if any(key in line for key in ['Steps:', 'CFG scale:', 'Sampler:', 'Model:', 'Size:']):
                        param_pairs = line.split(', ')
                        for pair in param_pairs:
                            if ':' in pair:
                                key, value = pair.split(':', 1)
                                params[key.strip()] = value.strip()
                        break
            
            return params, prompt, negative_prompt


        def read_image_metadata(image):
            if image is None:
                return "", "", "", 20, 7.0, "", "", "", -1, 512, 512, "{}", "{}", "No image uploaded."
            
            try:
                geninfo, items = images.read_info_from_image(image)

                all_metadata = {**{'parameters': geninfo}, **items} if geninfo else items

                info_html_content = ''
                for key, text in all_metadata.items():
                    if text:
                        info_html_content += f"""<div><p><b>{plaintext_to_html(str(key))}</b></p><p>{plaintext_to_html(str(text))}</p></div>""".strip() + "\n"
                
                if len(info_html_content) == 0:
                    info_html_content = "<div><p>Nothing found in the image.</p></div>"

                prompt = ""
                negative_prompt = ""
                steps_val = 20
                cfg_val = 7.0
                sampler_val = ""
                scheduler_val = ""
                model_val = ""
                seed_val = -1
                width_val = 512
                height_val = 512
                
                if geninfo:
                    params, prompt, negative_prompt = parse_parameters_string(geninfo)

                    try:
                        if 'Steps' in params:
                            steps_val = int(params['Steps'])
                        if 'CFG scale' in params:
                            cfg_val = float(params['CFG scale'])
                        if 'Sampler' in params:
                            sampler_val = params['Sampler']
                        if 'Schedule type' in params:
                            scheduler_val = params['Schedule type']
                        if 'Model' in params:
                            model_val = params['Model']
                        if 'Seed' in params:
                            seed_val = int(params['Seed'])
                        if 'Size' in params:
                            size_str = params['Size']
                            if 'x' in size_str:
                                w, h = size_str.split('x')
                                width_val = int(w.strip())
                                height_val = int(h.strip())
                    except (ValueError, IndexError):
                        pass

                custom_data = {}
                for key, value in all_metadata.items():
                    if key not in ['parameters'] and value:
                        custom_data[key] = str(value)
                
                metadata_json_str = json.dumps(all_metadata, indent=2, ensure_ascii=False)
                custom_fields_str = json.dumps(custom_data, indent=2, ensure_ascii=False) if custom_data else "{}"
                status = f"Successfully read metadata. Found {len(all_metadata)} fields."
                
                return (info_html_content, prompt, negative_prompt, steps_val, cfg_val, 
                       sampler_val, scheduler_val, model_val, seed_val, width_val, height_val,
                       metadata_json_str, custom_fields_str, status)
                
            except Exception as e:
                error_msg = f"Error reading metadata: {str(e)}"
                return ("", "", "", 20, 7.0, "", "", "", -1, 512, 512, "{}", "{}", error_msg)


        def save_image_with_metadata(image, prompt, negative_prompt, steps_val, 
                                   cfg_val, sampler_val, scheduler_val, model_val, seed_val, width_val, height_val, metadata_json_str, custom_fields_str):
            if image is None:
                return None, "No image to save.", None
            
            try:
                if not isinstance(image, Image.Image):
                    return None, "Invalid image format.", None

                if image.mode not in ('RGB', 'RGBA'):
                    output_img = image.convert('RGB')
                else:
                    output_img = image.copy()

                try:
                    custom_data = json.loads(custom_fields_str) if custom_fields_str and custom_fields_str.strip() else {}
                except:
                    custom_data = {}

                parameters_parts = []
                if prompt and str(prompt).strip():
                    parameters_parts.append(str(prompt).strip())
                
                if negative_prompt and str(negative_prompt).strip():
                    parameters_parts.append(f"Negative prompt: {str(negative_prompt).strip()}")

                tech_params = []
                try:
                    if steps_val and float(steps_val) > 0:
                        tech_params.append(f"Steps: {int(float(steps_val))}")
                except (ValueError, TypeError):
                    pass
                    
                try:
                    if cfg_val and float(cfg_val) > 0:
                        tech_params.append(f"CFG scale: {float(cfg_val)}")
                except (ValueError, TypeError):
                    pass
                    
                if sampler_val and str(sampler_val).strip():
                    tech_params.append(f"Sampler: {str(sampler_val).strip()}")
                if scheduler_val and str(scheduler_val).strip():
                    tech_params.append(f"Schedule type: {str(scheduler_val).strip()}")
                if model_val and str(model_val).strip():
                    tech_params.append(f"Model: {str(model_val).strip()}")
                    
                try:
                    if seed_val is not None and float(seed_val) >= 0:
                        tech_params.append(f"Seed: {int(float(seed_val))}")
                except (ValueError, TypeError):
                    pass
                    
                try:
                    if width_val and height_val and float(width_val) > 0 and float(height_val) > 0:
                        tech_params.append(f"Size: {int(float(width_val))}x{int(float(height_val))}")
                except (ValueError, TypeError):
                    pass
                
                if tech_params:
                    parameters_parts.append(", ".join(tech_params))
                
                parameters_string = "\n".join(parameters_parts)

                png_info = PngInfo()

                if parameters_string:
                    png_info.add_text("parameters", parameters_string)

                for key, value in custom_data.items():
                    if key and value and str(key).strip() and str(value).strip():
                        try:
                            png_info.add_text(str(key).strip(), str(value).strip())
                        except:
                            pass

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="metadata_edited_")
                output_img.save(temp_file.name, format='PNG', pnginfo=png_info)
                temp_file.close()

                buffer = BytesIO()
                output_img.save(buffer, format='PNG', pnginfo=png_info)
                buffer.seek(0)
                result_img = Image.open(buffer)
                result_img.load()
                buffer.close()
                
                status_msg = f"Successfully saved metadata to image! Go to Output Image tab for download."
                if parameters_string:
                    preview = parameters_string.replace('\n', ' | ')
                    if len(preview) > 100:
                        preview = preview[:97] + "..."
                    status_msg += f"<br>Preview: {preview}"

                return result_img, status_msg, temp_file.name
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Full error details: {error_details}")
                return None, f"Error saving metadata: {str(e)}", None


        def clear_all_metadata(image):
            if image is None:
                return None, "No image to process."
            
            try:
                buffer = BytesIO()

                if hasattr(image, 'format') and image.format == 'JPEG':
                    image.save(buffer, format='JPEG', quality=95)
                else:
                    image.save(buffer, format='PNG')
                
                buffer.seek(0)
                output_img = Image.open(buffer)
                output_img.load()
                buffer.close()
                
                return output_img, "All metadata removed from image, download in Output Image tab."
                
            except Exception as e:
                return None, f"Error clearing metadata: {str(e)}"


        def add_custom_field(custom_fields_str, key, value):
            if not key or not value or not key.strip() or not value.strip():
                return custom_fields_str, key, value
            
            try:
                custom_data = json.loads(custom_fields_str) if custom_fields_str and custom_fields_str.strip() else {}

                custom_data[key.strip()] = value.strip()

                updated_json = json.dumps(custom_data, indent=2, ensure_ascii=False)
                return updated_json, "", ""
                
            except Exception as e:
                return custom_fields_str, key, value


        read_metadata_btn.click(
            fn=read_image_metadata,
            inputs=[input_image],
            outputs=[info_html, prompt_text, negative_prompt_text, steps, cfg_scale, 
                    sampler, scheduler, model, seed, width, height, metadata_json, 
                    custom_fields_display, status_display]
        )
        
        save_metadata_btn.click(
            fn=save_image_with_metadata,
            inputs=[input_image, prompt_text, negative_prompt_text, steps, 
                   cfg_scale, sampler, scheduler, model, seed, width, height, 
                   metadata_json, custom_fields_display],
            outputs=[output_image, status_display, download_file]
        )
        
        clear_metadata_btn.click(
            fn=clear_all_metadata,
            inputs=[input_image],
            outputs=[output_image, status_display]
        )
        
        add_custom_btn.click(
            fn=add_custom_field,
            inputs=[custom_fields_display, custom_key, custom_value],
            outputs=[custom_fields_display, custom_key, custom_value]
        )

        input_image.change(
            fn=read_image_metadata,
            inputs=[input_image],
            outputs=[info_html, prompt_text, negative_prompt_text, steps, cfg_scale,
                    sampler, scheduler, model, seed, width, height, metadata_json, 
                    custom_fields_display, status_display]
        )

        return (input_image, info_html, prompt_text, negative_prompt_text, steps, cfg_scale,
                sampler, scheduler, model, seed, width, height, metadata_json, 
                custom_fields_display, output_image, status_display, download_file)
