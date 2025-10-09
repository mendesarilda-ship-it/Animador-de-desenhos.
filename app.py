import streamlit as st
from PIL import Image
import numpy as np

# --- CORREÇÃO CRÍTICA DE ERRO (PIL/Pillow > 9.0) ---
# Se a constante ANTIALIAS foi removida, a definimos como LANCZOS para manter a compatibilidade 
# com a versão 1.0.3 do MoviePy.
try:
    # Tenta usar a constante ANTIALIAS
    if not hasattr(Image, 'ANTIALIAS'):
        # Se não existir (versões novas do Pillow), usa LANCZOS
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    
    # Em versões muito novas, ANTIALIAS pode ter sido movida
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except AttributeError:
    # Fallback para LANCZOS se ANTIALIAS falhar totalmente
    Image.ANTIALIAS = Image.Resampling.LANCZOS


from moviepy.editor import ImageClip, concatenate_videoclips
import os
import tempfile

# --- 1. FUNÇÃO DE GERAÇÃO DE VÍDEO (O MOTOR DA IA) ---
def create_cartoon_animation(image_path, duration_sec, fps):
    """
    Cria uma animação de zoom e pan (movimento lateral) a partir de uma imagem.
    Usa o MoviePy para gerar o vídeo final.
    """
    try:
        # Carrega a imagem
        img = Image.open(image_path).convert("RGB")
        width, height = img.size
        
        # Converte a imagem PIL para um array numpy (formato que o MoviePy usa)
        np_img = np.array(img)

        # --- PARTE 1: Movimento de Zoom In (Clip 1) ---
        zoom_duration = duration_sec / 2
        final_scale = 1.2 # Fator de escala final (Zoom In de 1.0x para 1.2x)

        # 1. Define o Clip e a duração
        clip_zoom = ImageClip(np_img, duration=zoom_duration)

        # 2. Aplica a função de redimensionamento (resize) que depende do tempo (t)
        clip_zoom = clip_zoom.fx(
            lambda clip: clip.resize(
                lambda t: 1 + (final_scale - 1) * t / zoom_duration
            )
        )
        
        # 3. Centraliza a posição da imagem
        clip_zoom = clip_zoom.set_pos("center")
        
        # --- PARTE 2: Movimento de Pan Horizontal (Clip 2) ---
        pan_duration = duration_sec - zoom_duration
        
        # Define a função de pan (move o quadro de visualização)
        def pan_frame(t):
            # Calcula o percentual de tempo decorrido
            t_percent = t / pan_duration
            
            # Define o tamanho do corte (mantemos um zoom leve de 1.1x para o pan)
            crop_size_w = int(width / 1.1)
            crop_size_h = int(height / 1.1)
            
            # Posição inicial (x_start) e final (x_end) do canto superior esquerdo
            x_start = 0
            # x_end é o máximo que podemos mover para o lado sem sair da imagem
            x_end = width - crop_size_w
            
            # Posição x atual (Pan da esquerda para a direita)
            x_current = int(x_start + t_percent * (x_end - x_start))
            
            # y é constante (mantemos o topo do corte)
            y_current = 0 
            
            # Corta a imagem (crop)
            cropped_img = img.crop((x_current, y_current, x_current + crop_size_w, y_current + crop_size_h))
            
            # Retorna o frame como um array numpy
            return np.array(cropped_img)

        clip_pan = ImageClip(np_img, duration=pan_duration).set_make_frame(pan_frame)
        
        # Junta os dois clipes
        final_clip = concatenate_videoclips([clip_zoom, clip_pan], method="compose")
        final_clip = final_clip.set_fps(fps)

        # Salva o arquivo de vídeo temporário
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            output_path = temp_file.name
            
        final_clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False, 
            logger=None
        )
        
        return output_path

    except Exception as e:
        # Exibe uma mensagem de erro mais clara
        st.error(f"Erro ao gerar o vídeo: {e}")
        st.warning("Verifique se o 'packages.txt' com 'ffmpeg' está na raiz do seu repositório.")
        return None


# --- 2. INTERFACE STREAMLIT ---
st.set_page_config(page_title="Gerador de Vídeo Cartunesco", layout="wide")
st.title("🎬 Gerador de Vídeo Cartunesco (MoviePy)")

st.sidebar.header("Configurações")

# Carregamento da imagem 
uploaded_file = st.file_uploader(
    "1. Carregue sua imagem de desenho cartunesco:", 
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    # Salva o arquivo temporariamente para o MoviePy poder ler pelo caminho
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        image_path = tmp_file.name

    # Exibir a imagem carregada
    st.subheader("Imagem Carregada")
    st.image(image_path, use_column_width=True)
    
    st.subheader("Ajustes de Animação")
    
    # Parâmetros
    duration = st.sidebar.slider("Duração do Vídeo (segundos)", 
                                 min_value=3, max_value=10, value=5)
    fps = st.sidebar.slider("Quadros por Segundo (FPS)", 
                            min_value=10, max_value=30, value=24)
    
    if st.button("2. Gerar Animação"):
        video_output_path = None
        try:
            with st.spinner(f"Criando vídeo de {duration}s..."):
                video_output_path = create_cartoon_animation(image_path, duration, fps)
            
            if video_output_path:
                st.subheader("Vídeo Gerado!")
                
                # Leitura dos bytes do vídeo para exibição no Streamlit
                with open(video_output_path, "rb") as video_file:
                    video_bytes = video_file.read()
                
                st.video(video_bytes, format='video/mp4')
                
                # Opção de Download
                st.download_button(
                    label="Baixar Vídeo MP4",
                    data=video_bytes,
                    file_name="animacao_cartunesca.mp4",
                    mime="video/mp4"
                )
                
        finally:
            # Limpa os arquivos temporários, mesmo se houver erro
            if video_output_path and os.path.exists(video_output_path):
                os.unlink(video_output_path)
            if image_path and os.path.exists(image_path):
                 os.unlink(image_path)
            
else:
    st.info("Aguardando o upload da sua imagem cartunesca para começar.")
