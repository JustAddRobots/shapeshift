#!/usr/bin/env python3


export_config = {
    "exportShaderParams": False,
    "exportParameters": [
        {
            "parameters": {
                "fileFormat": "tga",
                "bitDepth": "8",
                "dithering": False,
                "paddingAlgorithm": "infinite"
            }
        }
    ],
    "exportPresets": [
        {
            "name": "Shapeshift",
            "maps": [
                {
                    "fileName": "T_$textureSet_D",
                    "channels": [
                        {
                            "destChannel": "L",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": "basecolor"
                        }
                    ]
                },
                {
                    "fileName": "T_$textureSet_M",
                    "channels": [
                        {
                            "destChannel": "R",
                            "srcChannel": "L",
                            "srcMapType": "meshMap",
                            "srcMapName": "ambient_occlusion"
                        },
                        {
                            "destChannel": "G",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": "roughness"
                        },
                        {
                            "destChannel": "B",
                            "srcChannel": "L",
                            "srcMapType": "documentMap",
                            "srcMapName": "metallic"
                        }
                    ]
                },
                {
                    "fileName": "T_$textureSet_N",
                    "channels": [
                        {
                            "destChannel": "L",
                            "srcChannel": "L",
                            "srcMapType": "meshMap",
                            "srcMapName": "normal_base"
                        }
                    ],
                    "parameter": {
                        "dithering": True
                    }
                }
            ]
        }
    ]
}


def get_export_config():
    return export_config
