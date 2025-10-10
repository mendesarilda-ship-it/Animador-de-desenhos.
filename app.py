import streamlit as st
from PIL import Image
import numpy as np

# --- 1. CORREÇÃO CRÍTICA DE ERRO (PIL/Pillow > 9.0) ---
# Garante a compatibilidade com MoviePy 1.0.3 resolvendo o erro ANTIALIAS
try:
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except AttributeError:
    Image.ANTIALIAS = Image.Resampling.LANCZOS


from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip
import os
import tempfile
import math

# --- 2. FUNÇÃO PRINCIPAL DE GERAÇÃO DE VÍDEO (AGORA COM RECORTES) ---
def create_cartoon_animation(parts, duration_sec, fps):
    """
    Cria uma animação de recortes (cutout animation) a partir de clipes de partes separadas.
    """
    try:
        clip_duration = duration_sec
        final_clips = []
        
        # ----------------------------------------------------------------------
        # PASSO 1: CARREGAR E PREPARAR AS PARTES NA ORDEM DE COMPOSIÇÃO (Fundo -> Frente)
        # ----------------------------------------------------------------------
        
        # O MoviePy compõe os clipes na ordem em que são listados.
        # Definiremos a ordem para montagem correta.
        
        # O "Vestido e Tronco" é a base, então ele deve ser o primeiro a ser processado.
        if 'Vestido e Tronco' not in parts:
            st.error("É necessário carregar o arquivo 'Vestido e Tronco' para iniciar a animação.")
            return None
        
        np_base_body = np.array(parts['Vestido e Tronco'].convert("RGBA"))
        clip_base_body = ImageClip(np_base_body, duration=clip_duration).set_pos(("center", "center"))
        video_size = clip_base_body.size # Define o tamanho final do vídeo baseado nesta peça
        final_clips.append(clip_base_body)

        # PERNAS (Podemos ter uma perna esquerda e uma perna direita, ou usar a mesma e espelhar)
        # Vamos usar 'Perna 1' e 'Perna 2' conforme seus uploads
        if 'Perna 1' in parts:
            np_perna1 = np.array(parts['Perna 1'].convert("RGBA"))
            clip_perna1 = ImageClip(np_perna1, duration=clip_duration)
            # POSICIONAMENTO DA PERNA 1 (AJUSTE MANUAL!)
            # Posicione a perna na parte inferior do corpo.
            clip_perna1 = clip_perna1.set_pos((video_size[0]*0.45, video_size[1]*0.65)) 
            final_clips.append(clip_perna1)

        if 'Perna 2' in parts:
            np_perna2 = np.array(parts['Perna 2'].convert("RGBA"))
            clip_perna2 = ImageClip(np_perna2, duration=clip_duration)
            # POSICIONAMENTO DA PERNA 2 (AJUSTE MANUAL!)
            # Posicione a perna na parte inferior do corpo, um pouco mais para a direita.
            clip_perna2 = clip_perna2.set_pos((video_size[0]*0.55, video_size[1]*0.65)) 
            final_clips.append(clip_perna2)


        # BRAÇO ESQUERDO (Exemplo de Animação: Rotação para simular um aceno leve)
        # Assumindo Image 1 como o braço esquerdo
        if 'Braço Esquerdo' in parts:
            np_braco_esq = np.array(parts['Braço Esquerdo'].convert("RGBA"))
            clip_braco_esq = ImageClip(np_braco_esq, duration=clip_duration)
            
            # POSICIONAMENTO DA JUNTA (AJUSTE MANUAL CRÍTICO!)
            # Esses valores (X, Y) precisam ser ajustados para o ponto do ombro na sua imagem de recorte
            # Baseado na sua imagem original, o ombro esquerdo está mais para a direita do centro.
            OMBRO_ESQ_X = video_size[0] * 0.45 # Ajuste
            OMBRO_ESQ_Y = video_size[1] * 0.35 # Ajuste
            
            # 1. POSIÇÃO DA PARTE (Onde o ombro vai estar na tela)
            # O ponto 'center=(0.1*clip_braco_esq.w, 0.1*clip_braco_esq.h)' é um palpite 
            # para o pivô do ombro dentro da imagem do braço.
            clip_braco_esq = clip_braco_esq.set_pos((OMBRO_ESQ_X, OMBRO_ESQ_Y))
            
            # 2. FUNÇÃO DE MOVIMENTO (Rotação: -10 graus a 10 graus)
            def get_rotation_esq(t):
                return 10 * math.sin(2 * math.pi * t / clip_duration) 

            # 3. APLICAR ROTAÇÃO
            # O 'center' no rotate FX define o ponto de pivô DENTRO da imagem do braço.
            # Você precisa ajustar esse ponto para onde o braço se conecta ao corpo.
            clip_braco_esq = clip_braco_esq.fx(
                lambda clip: clip.rotate(
                    get_rotation_esq, 
                    resample='bicubic', 
                    center=(clip.w * 0.1, clip.h * 0.1) # Ajuste: centro de rotação dentro da imagem do braço
                )
            )
            final_clips.append(clip_braco_esq)


        # BRAÇO DIREITO (Sem animação, apenas posicionamento)
        # Assumindo Image 6 como o braço direito
        if 'Braço Direito' in parts:
            np_braco_dir = np.array(parts['Braço Direito'].convert("RGBA"))
            clip_braco_dir = ImageClip(np_braco_dir, duration=clip_duration)
            # POSICIONAMENTO DA JUNTA (AJUSTE MANUAL!)
            OMBRO_DIR_X = video_size[0] * 0.55 
            OMBRO_DIR_Y = video_size[1] * 0.35 
            clip_braco_dir = clip_braco_dir.set_pos((OMBRO_DIR_X, OMBRO_DIR_Y))
            final_clips.append(clip_braco_dir)
            
        # DEDOS (Seria uma sub-parte de uma mão. Para simplificar, vou tratar como peça separada)
        if 'Dedos' in parts:
            np_dedos = np.array(parts['Dedos'].convert("RGBA"))
            clip_dedos = ImageClip(np_dedos, duration=clip_duration)
            # Posicione os dedos sobre a Mão Esquerda (assumindo que seja essa)
            # Os offsets são em relação à posição da mão/braço
            clip_dedos = clip_dedos.set_pos((OMBRO_ESQ_X + 50, OMBRO_ESQ_Y + 100)) # Ajuste
            final_clips.append(clip_dedos)

        # CABEÇA (Sobre o tronco)
        if 'Cabeça' in parts:
            np_cabeca = np.array(parts['Cabeça'].convert("RGBA"))
            clip_cabeca = ImageClip(np_cabeca, duration=clip_duration)
            # Posicionamento da cabeça (ajuste para o pescoço)
            clip_cabeca = clip_cabeca.set_pos(("center", video_size[1]*0.15)) # 15% do topo
            final_clips.append(clip_cabeca)
            
        # OLHOS (Sobre a cabeça)
        if 'Olhos' in parts:
            np_olhos = np.array(parts['Olhos'].convert("RGBA"))
            clip_olhos = ImageClip(np_olhos, duration=clip_duration)
            # Posicionamento dos olhos (ajuste para ficarem na face da cabeça)
            clip_olhos = clip_olhos.set_pos(("center", video_size[1]*0.25)) # Ajuste
            final_clips.append(clip_olhos)


        # ----------------------------------------------------------------------
        # PASSO 2: COMPOSIÇÃO FINAL
        # ----------------------------------------------------------------------
        
        # Junta todos os clipes de partes do corpo (estáticos e animados)
        # Garante que o CompositeVideoClip tem o tamanho correto
        final_clip = CompositeVideoClip(final_clips, size=video_size)
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
        st.error(f"Erro ao gerar o vídeo: {e}")
        st.warning("Verifique se você carregou todas as partes necessárias e se o 'packages.txt' com 'ffmpeg' está na raiz.")
        return None

# --- 3. INTERFACE STREAMLIT COM MÚLTIPLOS U
