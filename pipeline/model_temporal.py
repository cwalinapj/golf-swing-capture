import torch
import torch.nn as nn
import torchvision.models as models


# -------------------------
# Frame Encoder (CNN)
# -------------------------
class FrameEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        base = models.resnet18(pretrained=True)
        self.encoder = nn.Sequential(*list(base.children())[:-1])

    def forward(self, x):
        B, T, C, H, W = x.shape
        x = x.view(B * T, C, H, W)

        feats = self.encoder(x)
        feats = feats.view(B, T, -1)

        return feats  # (B, T, 512)


# -------------------------
# Temporal Transformer
# -------------------------
class TemporalEncoder(nn.Module):
    def __init__(self, dim=512, heads=4, layers=2):
        super().__init__()

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=dim,
            nhead=heads,
            batch_first=True
        )

        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=layers)

    def forward(self, x):
        return self.transformer(x)  # (B, T, dim)


# -------------------------
# Camera Encoder (CNN + Time)
# -------------------------
class CameraTemporal(nn.Module):
    def __init__(self):
        super().__init__()
        self.frame_encoder = FrameEncoder()
        self.temporal = TemporalEncoder()

    def forward(self, x):
        # x: (B, T, C, H, W)
        feats = self.frame_encoder(x)
        feats = self.temporal(feats)

        # take final token (or mean)
        return feats.mean(dim=1)  # (B, 512)


# -------------------------
# Cross-Camera Attention
# -------------------------
class CrossCameraAttention(nn.Module):
    def __init__(self, dim=512, heads=4):
        super().__init__()

        self.attn = nn.MultiheadAttention(
            embed_dim=dim,
            num_heads=heads,
            batch_first=True
        )

    def forward(self, x):
        # x: (B, num_cameras, dim)
        out, _ = self.attn(x, x, x)
        return out.mean(dim=1)  # fuse cameras


# -------------------------
# Full Model
# -------------------------
class MultiCameraTemporalModel(nn.Module):
    def __init__(self, num_cameras=4):
        super().__init__()

        self.cameras = nn.ModuleList([CameraTemporal() for _ in range(num_cameras)])
        self.cross_attn = CrossCameraAttention()

        self.head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 3)  # ball_speed, launch_angle, spin_rate
        )

    def forward(self, inputs):
        cam_feats = []

        for i, cam in enumerate(self.cameras):
            feat = cam(inputs[i])  # (B, 512)
            cam_feats.append(feat)

        x = torch.stack(cam_feats, dim=1)  # (B, N, 512)

        x = self.cross_attn(x)

        return self.head(x)
