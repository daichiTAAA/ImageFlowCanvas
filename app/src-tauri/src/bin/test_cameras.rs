use nokhwa::utils::ApiBackend;
use nokhwa::query;

fn main() {
    println!("=== Nokhwa USB Camera Detection Test ===");
    
    let backends = vec![
        nokhwa::utils::ApiBackend::Auto,
        nokhwa::utils::ApiBackend::AVFoundation,
    ];
    
    for backend in backends {
        println!("\n--- Testing Backend: {:?} ---", backend);
        match query(backend) {
            Ok(cameras) => {
                println!("Found {} cameras with backend {:?}", cameras.len(), backend);
                for (i, camera_info) in cameras.iter().enumerate() {
                    println!("  Camera {}: {}", i, camera_info.human_name());
                    println!("    Description: {}", camera_info.description());
                    println!("    Index: {:?}", camera_info.index());
                    println!("    Misc: {}", camera_info.misc());
                }
            }
            Err(e) => {
                println!("Error with backend {:?}: {}", backend, e);
            }
        }
    }
    
    // Also test system profiler
    #[cfg(target_os = "macos")]
    {
        println!("\n=== System Profiler Check ===");
        use std::process::Command;
        
        match Command::new("system_profiler").arg("SPCameraDataType").output() {
            Ok(output) => {
                let camera_info = String::from_utf8_lossy(&output.stdout);
                println!("System cameras found:");
                println!("{}", camera_info);
            }
            Err(e) => {
                println!("System profiler error: {}", e);
            }
        }
    }
}
