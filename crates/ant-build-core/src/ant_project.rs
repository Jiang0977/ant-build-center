use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BuildFileMetadata {
    pub project_name: String,
    pub default_target: String,
    pub targets: Vec<String>,
}

pub fn inspect_build_file(path: &Path) -> io::Result<BuildFileMetadata> {
    let content = fs::read_to_string(path)?;
    let document = roxmltree::Document::parse(&content)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    let root = document.root_element();

    if root.tag_name().name() != "project" {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "root element is not <project>",
        ));
    }

    let project_name = root
        .attribute("name")
        .unwrap_or("Unnamed Project")
        .to_string();
    let default_target = root.attribute("default").unwrap_or_default().to_string();
    let targets = root
        .children()
        .filter(|node| node.is_element() && node.tag_name().name() == "target")
        .filter_map(|target| target.attribute("name").map(str::to_string))
        .collect();

    Ok(BuildFileMetadata {
        project_name,
        default_target,
        targets,
    })
}
