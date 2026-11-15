import os
import win32com.client

# ==============================================================================
# PowerPoint Animation & Transition Automation for Nemov Presentation 1
# ==============================================================================
# EntryEffect constants:
#   ppEffectFade = 1793
#   ppEffectPushLeft = 3845
#   ppEffectPushRight = 3846
#   ppEffectWipeRight = 2562
#
# MsoAnimEffect constants:
#   msoAnimEffectFade = 10
#   msoAnimEffectAscend = 62 (Rise / Float In)
#   msoAnimEffectFadedZoom = 56
#   msoAnimEffectZoom = 24
#   msoAnimEffectWipe = 22
#   msoAnimEffectFly = 2
#
# MsoAnimTriggerType:
#   msoAnimTriggerOnClick = 1
#   msoAnimTriggerWithPrevious = 2
#   msoAnimTriggerAfterPrevious = 3
# ==============================================================================

def apply_animations(pptx_path: str, output_path: str, trigger_mode: str = "click"):
    """
    trigger_mode:
      - 'click': Main content cards appear on user click (standard for oral defense).
      - 'auto': Main content cards appear sequentially automatically with smooth delays.
    """
    ppt = win32com.client.Dispatch("PowerPoint.Application")
    try:
        abs_in = os.path.abspath(pptx_path)
        abs_out = os.path.abspath(output_path)
        pres = ppt.Presentations.Open(abs_in, WithWindow=False)
        
        total_slides = pres.Slides.Count
        print(f"Applying animations to {total_slides} slides (Trigger mode: {trigger_mode})...")
        
        for slide_num in range(1, total_slides + 1):
            slide = pres.Slides(slide_num)
            seq = slide.TimeLine.MainSequence
            
            # Clear existing animations if any
            while seq.Count > 0:
                seq(1).Delete()
                
            # 1. Slide Transition
            trans = slide.SlideShowTransition
            trans.AdvanceOnClick = -1 # msoTrue
            
            if slide_num == 1:
                # Slide 1: Smooth Fade
                trans.EntryEffect = 1793 # ppEffectFade
                trans.Duration = 0.8
                
                # Shapes on Slide 1:
                # Shapes 1, 2, 3: Tricolor strips (Green, White, Red)
                # Shape 4: Logo Picture
                # Shape 5: Title Textbox
                # Shape 6: Info Card
                
                # Top tricolor strips: Wipe from left or Fade with previous
                for strip_idx in [1, 2, 3]:
                    eff_strip = seq.AddEffect(slide.Shapes(strip_idx), 10, 0, 2) # Fade, WithPrevious
                    eff_strip.Timing.Duration = 0.4
                    
                # Logo: Faded Zoom / Gentle Zoom
                eff_logo = seq.AddEffect(slide.Shapes(4), 56, 0, 3) # FadedZoom, AfterPrevious
                eff_logo.Timing.Duration = 0.6
                
                # Title Textbox: Ascend / Float In
                eff_title = seq.AddEffect(slide.Shapes(5), 62, 0, 2) # Ascend, WithPrevious
                eff_title.Timing.Duration = 0.7
                eff_title.Timing.TriggerDelayTime = 0.15
                
                # Info Card: Smooth Fade
                eff_info = seq.AddEffect(slide.Shapes(6), 10, 0, 3) # Fade, AfterPrevious
                eff_info.Timing.Duration = 0.5
                eff_info.Timing.TriggerDelayTime = 0.1
                
            else:
                # Slides 2 to 12
                # Transition: Smooth Fade (or Push for diagrams)
                if slide_num in [6, 7, 8, 9]:
                    trans.EntryEffect = 3845 # ppEffectPushLeft (subtle directional flow for diagrams)
                    trans.Duration = 0.55
                else:
                    trans.EntryEffect = 1793 # ppEffectFade
                    trans.Duration = 0.5
                    
                # Header shapes:
                # Shapes 1, 2, 3: Tricolor strips (instant / WithPrevious)
                # Shape 4: Category badge ("● فاز ۱...")
                # Shape 5: Title Textbox
                # Shape 6: Subtitle Textbox
                # Shape 7: Logo Picture (top-left)
                
                # Header elements appear automatically on slide load
                eff_cat = seq.AddEffect(slide.Shapes(4), 10, 0, 2) # Fade, WithPrevious
                eff_cat.Timing.Duration = 0.35
                
                eff_title = seq.AddEffect(slide.Shapes(5), 10, 0, 2) # Fade, WithPrevious
                eff_title.Timing.Duration = 0.35
                
                eff_sub = seq.AddEffect(slide.Shapes(6), 10, 0, 2) # Fade, WithPrevious
                eff_sub.Timing.Duration = 0.35
                
                eff_logo = seq.AddEffect(slide.Shapes(7), 10, 0, 2) # Fade, WithPrevious
                eff_logo.Timing.Duration = 0.35
                
                # Content Cards: Shapes from index 8 up to slide.Shapes.Count
                total_shapes = slide.Shapes.Count
                card_shapes = [slide.Shapes(i) for i in range(8, total_shapes + 1)]
                
                card_trigger = 1 if trigger_mode == "click" else 3 # OnClick vs AfterPrevious
                
                for c_idx, card_shape in enumerate(card_shapes):
                    # For oral defense:
                    # If trigger_mode == 'click': each card is triggered on click
                    # If trigger_mode == 'auto': card 0 starts AfterPrevious, subsequent AfterPrevious with delay
                    eff_card = seq.AddEffect(card_shape, 62, 0, card_trigger) # Ascend / Float In
                    eff_card.Timing.Duration = 0.5
                    if trigger_mode == "auto":
                        eff_card.Timing.TriggerDelayTime = 0.2
                    eff_card.Timing.SmoothStart = -1
                    eff_card.Timing.SmoothEnd = -1
                    
            print(f"Slide {slide_num} configured: {seq.Count} animation effects, transition={trans.EntryEffect}")
            
        pres.SaveAs(abs_out)
        pres.Close()
        print(f"\nPresentation successfully saved to: {abs_out}")
    finally:
        ppt.Quit()

if __name__ == "__main__":
    src = "C:/Users/user/Desktop/Nemov_Presentation_1.pptx"
    out = "C:/Users/user/Desktop/Nemov_Presentation_1_Animated.pptx"
    apply_animations(src, out, trigger_mode="click")
