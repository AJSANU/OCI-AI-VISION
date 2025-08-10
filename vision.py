import base64
import streamlit as st
import oci
from PIL import Image, ImageDraw
import io

# -------- Color Palette --------
ANNOTATE_COLORS = [
    "red", "blue", "green", "purple", "orange", "magenta", "cyan", "lime", "brown", "gold"
]

# -- Streamlit UI Setup --
st.set_page_config(page_title="Smart Image Analyzer", layout="wide")
st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(135deg,#e9f5fe 0,#e1f7e7 100%);}
    .main > div {padding-top: 2rem;}
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    "<h1 style='text-align:center; color:#0a9396;'>Smart Image Analyzer</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<h4 style='text-align:center; color:#555';>Using Oracle Cloud Infrastructure Vision AI and Streamlit</h4>",
    unsafe_allow_html=True,
)
st.markdown("---")

st.sidebar.title("How to Use")
st.sidebar.info(
    "1. Upload an image (JPG/PNG)\n"
    "2. Select analysis type\n"
    "3. Click **Analyze**.\n\n"
    "Results will appear with highlights/annotations below.\n\n"
    "✨ Try images with people for Face Detection!\n"
)
st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.markdown(
    "Made with ❤️ using [OCI AI Vision](https://docs.oracle.com/en-us/iaas/Content/ai-vision/home.htm)\n\n_By Abhishek Jha, 10/08/2025"
)

# --- OCI Setup ---
compartment_id = '<Your compartment>'  # Replace with your real OCID
config = oci.config.from_file("config") # Replace with your config
ai_vision_client = oci.ai_vision.AIServiceVisionClient(config)

@st.cache_resource(show_spinner='Analyzing image...')
def analyze_with_oci(image_data, analysis_type):
    image_data_b64 = base64.b64encode(image_data).decode("utf-8")
    features = []
    if analysis_type == "Image Classification":
        features = [oci.ai_vision.models.ImageClassificationFeature(feature_type="IMAGE_CLASSIFICATION", max_results=5)]
    elif analysis_type == "Object Detection":
        features = [oci.ai_vision.models.ImageObjectDetectionFeature(feature_type="OBJECT_DETECTION")]
    elif analysis_type == "Text Extraction":
        features = [oci.ai_vision.models.ImageTextDetectionFeature(feature_type="TEXT_DETECTION")]
    elif analysis_type == "Face Detection":
        features = [oci.ai_vision.models.FaceDetectionFeature(feature_type="FACE_DETECTION")]
    analyze_image_details = oci.ai_vision.models.AnalyzeImageDetails(
        features=features,
        image=oci.ai_vision.models.InlineImageDetails(source="INLINE", data=image_data_b64),
        compartment_id=compartment_id,
    )
    response = ai_vision_client.analyze_image(analyze_image_details=analyze_image_details)
    return response

# Session state for balloons, last file/type
if 'balloons_shown' not in st.session_state:
    st.session_state.balloons_shown = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'last_file_name' not in st.session_state:
    st.session_state.last_file_name = None
if 'last_analysis_type' not in st.session_state:
    st.session_state.last_analysis_type = None

uploaded_file = st.file_uploader("📤 Upload an Image", type=["jpg", "jpeg", "png"])
analysis_type = st.selectbox(
    "🔍 Select Analysis Type",
    ["Image Classification", "Object Detection", "Text Extraction", "Face Detection"]
)

st.markdown("---")

if uploaded_file:
    image_data = uploaded_file.read()

    # Clear cache if new image or analysis type
    new_job = (st.session_state.last_file_name != uploaded_file.name or
               st.session_state.last_analysis_type != analysis_type)
    if new_job:
        st.session_state.analysis_results = None
        st.session_state.balloons_shown = False

    if st.button("🚀 Analyze") or st.session_state.analysis_results is not None:
        if st.session_state.analysis_results is None:
            with st.spinner("Analyzing image ..."):
                result = analyze_with_oci(image_data, analysis_type)
                st.session_state.analysis_results = result
                st.session_state.last_file_name = uploaded_file.name
                st.session_state.last_analysis_type = analysis_type
                st.session_state.balloons_shown = False
            # Show balloon only right after OCI result:
            if not st.session_state.balloons_shown:
                st.balloons()
                st.session_state.balloons_shown = True
        else:
            result = st.session_state.analysis_results

        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        w, h = image.size

        # UI Layout
        col1, col2 = st.columns([1, 1])
        data = result.data

        show_labels = []

        ######### Side 1: Result selection column
        with col1:
            st.subheader("🎯 Results")
            selected_indices = []

            if analysis_type == "Image Classification":
                if hasattr(data, "labels") and data.labels:
                    st.markdown("**Top 5 Predicted Labels:**")
                    for label in data.labels:
                        st.info(f"**{label.name}** · _Confidence:_ {label.confidence:.2f}")
                else:
                    st.warning("No classification results returned.")

            elif analysis_type == "Object Detection":
                if hasattr(data, "image_objects") and data.image_objects:
                    object_options = [
                        f"{detected.name} (Confidence: {detected.confidence:.2f})"
                        for detected in data.image_objects
                    ]
                    selected_objects = st.multiselect(
                        "Select object(s) to highlight",
                        object_options,
                        default=[],
                        key=f"selected_object_{uploaded_file.name}",
                    )
                    selected_indices = [object_options.index(obj) for obj in selected_objects]
                else:
                    st.warning("No objects detected.")
                    selected_indices = []

            elif analysis_type == "Text Extraction":
                words = getattr(getattr(data, "image_text", None), "words", [])
                if words:
                    word_options = [
                        f"{word.text} (Confidence: {word.confidence:.2f})"
                        for word in words
                    ]
                    selected_words = st.multiselect(
                        "Select word(s) to highlight",
                        word_options,
                        default=[],
                        key=f"selected_word_{uploaded_file.name}",
                    )
                    selected_indices = [word_options.index(word) for word in selected_words]
                    # Show full text block
                    extracted_text = getattr(getattr(data, "image_text", None), "text", None)
                    if extracted_text:
                        st.markdown("**Full Extracted Text:**")
                        st.code(extracted_text)
                else:
                    st.warning("No text detected.")
                    selected_indices = []

            elif analysis_type == "Face Detection":
                faces = getattr(data, "detected_faces", [])
                if faces:
                    face_options = [
                        f"Face {idx+1} (Confidence: {face.confidence:.2f})"
                        for idx, face in enumerate(faces)
                    ]
                    selected_faces = st.multiselect(
                        "Select face(s) to highlight",
                        face_options,
                        default=[],
                        key=f"selected_face_{uploaded_file.name}",
                    )
                    selected_indices = [face_options.index(face) for face in selected_faces]
                else:
                    st.warning("No faces detected.")
                    selected_indices = []

        ######### Side 2: Annotated image column
        with col2:
            st.subheader("🖼️ Annotated Image")
            annotated_image = image.copy()
            draw = ImageDraw.Draw(annotated_image)

            if analysis_type == "Object Detection":
                if hasattr(data, "image_objects") and data.image_objects and selected_indices:
                    for draw_i, idx in enumerate(selected_indices):
                        color = ANNOTATE_COLORS[draw_i % len(ANNOTATE_COLORS)]
                        detected = data.image_objects[idx]
                        box = detected.bounding_polygon.normalized_vertices
                        points = [(int(v.x * w), int(v.y * h)) for v in box]
                        draw.polygon(points, outline=color, width=4)
                        draw.text((points[0][0], points[0][1] - 18), f"{detected.name}\n{detected.confidence:.2f}", fill=color)
                        show_labels.append(f"<span style='color:{color}'><b>{detected.name}</b></span> · _Confidence:_ {detected.confidence:.2f}")
                    st.image(annotated_image, caption="Selected Objects Highlighted", use_column_width=True)
                    if show_labels:
                        st.markdown("**Selected Object(s):**")
                        for label in show_labels:
                            st.markdown(label, unsafe_allow_html=True)
                else:
                    st.image(annotated_image, caption="Select objects to highlight.", use_column_width=True)

            elif analysis_type == "Text Extraction":
                words = getattr(getattr(data, "image_text", None), "words", [])
                if words and selected_indices:
                    for idx in selected_indices:
                        word = words[idx]
                        box = word.bounding_polygon.normalized_vertices
                        points = [(int(v.x * w), int(v.y * h)) for v in box]
                        draw.rectangle([points[0], points[2]], outline="green", width=3)
                        draw.text((points[0][0], points[0][1] - 15), f"{word.text}\n{word.confidence:.2f}", fill="green")
                        show_labels.append(f"**{word.text}** · _Confidence:_ {word.confidence:.2f}")
                    st.image(annotated_image, caption="Selected Words Highlighted", use_column_width=True)
                    if show_labels:
                        st.markdown("**Selected Word(s):**")
                        for label in show_labels:
                            st.markdown(label)
                else:
                    st.image(annotated_image, caption="Select text to highlight.", use_column_width=True)

            elif analysis_type == "Face Detection":
                faces = getattr(data, "detected_faces", [])
                if faces and selected_indices:
                    for draw_i, idx in enumerate(selected_indices):
                        color = ANNOTATE_COLORS[draw_i % len(ANNOTATE_COLORS)]
                        face = faces[idx]
                        box = face.bounding_polygon.normalized_vertices
                        points = [(int(v.x * w), int(v.y * h)) for v in box]
                        draw.polygon(points, outline=color, width=4)
                        draw.text((points[0][0], points[0][1] - 15), f"Face {idx + 1}\n{face.confidence:.2f}", fill=color)
                        show_labels.append(f"<span style='color:{color}'><b>Face {idx + 1}</b></span> · _Confidence:_ {face.confidence:.2f}")
                    st.image(annotated_image, caption="Selected Faces Highlighted", use_column_width=True)
                    if show_labels:
                        st.markdown("**Selected Face(s):**")
                        for label in show_labels:
                            st.markdown(label, unsafe_allow_html=True)
                else:
                    st.image(annotated_image, caption="Select faces to highlight.", use_column_width=True)

            elif analysis_type == "Image Classification":
                st.image(annotated_image, caption="Classification Complete", use_column_width=True)

        st.success("✅ Analysis Complete!")

else:
    st.info("👈 Please upload an image to begin.")
