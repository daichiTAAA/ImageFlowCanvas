// Simple camera detection test
use nokhwa::utils::ApiBackend;
use nokhwa::query;

fn main() {
    println!("=== カメラ検出テスト ===");
    
    // Test Auto backend
    println!("Auto backend:");
    match query(ApiBackend::Auto) {
        Ok(cameras) => {
            println!("  {}台のカメラを発見", cameras.len());
            for (i, camera) in cameras.iter().enumerate() {
                println!("    {}: {} - {}", i, camera.human_name(), camera.description());
                println!("       Index: {:?}", camera.index());
                println!("       Misc: {}", camera.misc());
            }
        }
        Err(e) => {
            println!("  エラー: {}", e);
        }
    }
    
    // Test AVFoundation backend specifically
    #[cfg(target_os = "macos")]
    {
        println!("\nAVFoundation backend:");
        match query(ApiBackend::AVFoundation) {
            Ok(cameras) => {
                println!("  {}台のカメラを発見", cameras.len());
                for (i, camera) in cameras.iter().enumerate() {
                    println!("    {}: {} - {}", i, camera.human_name(), camera.description());
                    println!("       Index: {:?}", camera.index());
                    println!("       Misc: {}", camera.misc());
                }
            }
            Err(e) => {
                println!("  エラー: {}", e);
            }
        }
    }
}
