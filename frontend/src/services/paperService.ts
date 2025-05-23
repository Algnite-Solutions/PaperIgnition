import Taro from '@tarojs/taro'
import { API_BASE_URL, API_ENDPOINTS } from '../config/api'

// 模拟论文内容 - 从 generated_blog.md 获取的内容
const BLOG_CONTENT = `
Okay, here is a blog post summarizing the TigerVector paper, incorporating only the specified figures and adhering to your formatting requirements.

---

## TigerVector: Bringing High-Performance Vector Search to Graph Databases for Advanced RAG

Retrieval-Augmented Generation (RAG) has become a cornerstone for grounding Large Language Models (LLMs) with external data. While traditional RAG often relies on vector databases storing semantic embeddings, this approach can struggle with complex queries that require understanding relationships between data points – a strength of graph databases.

Enter VectorGraphRAG, a promising hybrid approach that combines the power of vector search for semantic similarity with graph traversal for structural context. The paper "TigerVector: Supporting Vector Search in Graph Databases for Advanced RAGs" introduces TigerVector, a novel system that integrates vector search directly into TigerGraph, a distributed graph database. This unified approach aims to overcome the limitations of using separate systems, offering benefits like data consistency, reduced silos, and streamlined hybrid queries.

Integrating high-performance vector search into a graph database is challenging. TigerVector tackles this through several key innovations:

**A Unified Data Model:** TigerVector introduces a new \`embedding\` attribute type for vertices. This isn't just a list of floats; it explicitly manages crucial metadata like dimensionality, the model used, index type, and similarity metric. This dedicated type facilitates managing different types of embeddings and ensures compatibility during queries.

**Decoupled Storage:** Recognizing that vector embeddings are often much larger than other attributes, TigerVector stores vectors separately in "embedding segments." These segments mirror the vertex partitioning of the graph, ensuring related vector and graph data reside together for efficient processing. This decoupling also optimizes updates and index management.

![Figure 3](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Decoupled Storage. Vectors within a vertex segment (left) are stored separately in another embedding segment (right), while keeping the same ids.

**Leveraging MPP Architecture:** Built within TigerGraph's Massively Parallel Processing (MPP) architecture, TigerVector distributes vector data and processing across multiple machines. Vector indexes (currently supporting HNSW) are built per segment, and queries are parallelized, with results merged by a coordinator.
![Figure 5](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Distributed Query Processing. The coordinator prepares top-k vector search requests in the send queue and dispatches requests to worker servers. Each worker conducts top-k search locally and sends IDs and distances as results back to the response pool in the coordinator.

**GSQL Integration:** TigerVector integrates vector search into TigerGraph's GSQL query language. This includes adding \`VECTOR_DIST\` to \`ORDER BY...LIMIT\` syntax for declarative search and introducing a flexible \`VectorSearch()\` function. This function allows vector search results to be easily composed with graph query blocks, enabling complex hybrid queries.

**Advanced Hybrid Search:** TigerVector supports powerful query patterns beyond simple vector similarity, including filtered vector search and vector search on graph patterns. The \`VectorSearch()\` function can accept a vertex set from a graph query as a filter, allowing users to find similar items *within* a specific graph context (e.g., find similar posts written by people Alice knows).
![Figure 6](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Demonstration of Combing Community Detection and Vector Search. The Person vertices are partitioned into three communities, colored green, blue, and yellow. The top-k Posts from each community are colored red.

**Efficient Updates:** TigerVector supports transactional updates to vector data, leveraging TigerGraph's MVCC scheme and employing background vacuum processes to incrementally merge delta records into vector indexes. This ensures updates are atomic and efficient.

**Performance:** The paper presents extensive experiments comparing TigerVector with other graph databases supporting vector search (Neo4j, Amazon Neptune) and a specialized vector database (Milvus).
![Figure 7](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Throughput Evaluation on SIFT100M and Deep100M. TigerVector significantly outperforms Neo4j and Amazon Neptune in throughput and recall for vector search.
![Figure 8](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Latency Evaluation on SIFT100M and Deep100M. TigerVector shows significantly lower latency compared to Neo4j and Amazon Neptune.
TigerVector demonstrates performance comparable to, and sometimes even higher than, Milvus, a specialized vector database, particularly in throughput.

**Scalability:** Experiments show TigerVector scales effectively with both the number of nodes and dataset size, leveraging its distributed architecture.
![Figure 9](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Node Scalability. TigerVector exhibits near-linear throughput gain when scaling the number of machines.
![Figure 10](https://cdn.pixabay.com/photo/2025/05/07/18/46/lake-9585821_1280.jpg): Data Size Scalability. Throughput decreases roughly proportionally as the dataset size scales by 10x, demonstrating good scalability.

In conclusion, TigerVector represents a significant step towards a unified platform for graph and vector data, enabling powerful hybrid searches essential for advanced RAG applications. Its performance is competitive with specialized vector databases and significantly surpasses other graph databases with vector capabilities. TigerVector was integrated into TigerGraph v4.2, released in December 2024.
`

// 推荐页面的论文数据
const recommendedPapers = [
  {
    id: '1',
    title: 'TigerVector: Bringing High-Performance Vector Search to Graph Databases for Advanced RAG',
    authors: ['Jing Zhang', 'Victor Lee', 'Zhiqi Chen', 'Tianyi Zhang'],
    abstract: 'This paper introduces TigerVector, a novel system that integrates vector search directly into TigerGraph, a distributed graph database. This unified approach aims to overcome the limitations of using separate systems, offering benefits like data consistency, reduced silos, and streamlined hybrid queries for advanced RAG applications.',
    tags: ['Graph Databases', 'Vector Search', 'RAG', 'Performance'],
    submittedDate: '15 May, 2025',
    publishDate: 'May 2025',
    comments: 'Accepted at SIGMOD 2025'
  },
  {
    id: '2',
    title: 'CLOG-CD: Curriculum Learning based on Oscillating Granularity of Class Decomposed Medical Image Classification',
    authors: ['Asmaa Abbas', 'Mohamed Gaber', 'Mohammed M. Abdelsamea'],
    abstract: 'In this paper, we have also investigated the classification performance of our proposed method based on different acceleration factors and pace function curricula. We used two pre-trained networks, ResNet-50 and DenseNet-121, as the backbone for CLOG-CD. The results with ResNet-50 show that CLOG-CD has the ability to improve classification performance significantly.',
    tags: ['Medical Imaging', 'Curriculum Learning', 'Deep Learning'],
    submittedDate: '3 May, 2025',
    publishDate: 'May 2025',
    comments: 'Published in: IEEE Transactions on Emerging Topics in Computing'
  },
  {
    id: '3',
    title: 'Attention-Based Feature Fusion for Visual Odometry with Unsupervised Scale Recovery',
    authors: ['Liu Wei', 'Zhang Chen', 'Wang Mei'],
    abstract: 'We present a novel approach for visual odometry that integrates attention mechanisms to fuse features from multiple sources. Our method addresses the scale ambiguity problem in monocular visual odometry through an unsupervised learning framework. Experimental results on KITTI dataset demonstrate superior performance compared to existing methods.',
    tags: ['Visual Odometry', 'Attention Mechanism', 'Unsupervised Learning'],
    submittedDate: '28 April, 2025',
    publishDate: 'April 2025',
    comments: 'To appear in International Conference on Robotics and Automation 2025'
  },
  {
    id: '4',
    title: 'FedMix: Adaptive Knowledge Distillation for Personalized Federated Learning',
    authors: ['Sarah Johnson', 'David Chen', 'Michael Brown'],
    abstract: 'This paper introduces FedMix, a novel framework for personalized federated learning that employs adaptive knowledge distillation to balance model personalization and global knowledge sharing. Our approach dynamically adjusts the knowledge transfer between global and local models based on client data distribution characteristics.',
    tags: ['Federated Learning', 'Knowledge Distillation', 'Personalization'],
    submittedDate: '15 April, 2025',
    publishDate: 'April 2025',
    comments: 'Accepted at International Conference on Machine Learning 2025'
  }
]

/**
 * 获取论文列表
 */
export const getPapers = async () => {
  try {
    // 在实际环境中，这里会调用真实的 API
    // const response = await Taro.request({
    //   url: `${API_BASE_URL}${API_ENDPOINTS.PAPERS.LIST}`,
    //   method: 'GET'
    // })
    // return response.data

    // 模拟 API 响应
    return {
      statusCode: 200,
      data: recommendedPapers
    }
  } catch (error) {
    console.error('获取论文列表失败', error)
    throw error
  }
}

/**
 * 获取论文详情
 * @param id 论文ID
 */
export const getPaperDetail = async (id: string) => {
  try {
    // 在实际环境中，这里会调用真实的 API
    // const response = await Taro.request({
    //   url: `${API_BASE_URL}${API_ENDPOINTS.PAPERS.DETAIL(id)}`,
    //   method: 'GET'
    // })
    // return response.data

    // 模拟 API 响应
    const paper = recommendedPapers.find(p => p.id === id)
    if (!paper) {
      throw new Error('论文不存在')
    }
    
    return {
      statusCode: 200,
      data: paper
    }
  } catch (error) {
    console.error('获取论文详情失败', error)
    throw error
  }
}

/**
 * 获取论文内容（Markdown格式）
 * @param id 论文ID
 */
export const getPaperContent = async (id: string) => {
  try {
    // 在实际环境中，这里会调用真实的 API
    // const response = await Taro.request({
    //   url: `${API_BASE_URL}${API_ENDPOINTS.PAPERS.CONTENT(id)}`,
    //   method: 'GET'
    // })
    // return response.data

    // 检查论文ID是否存在
    const paper = recommendedPapers.find(p => p.id === id)
    if (!paper) {
      return {
        statusCode: 404,
        error: '论文内容不存在'
      }
    }
    
    // 为每个论文都返回相同的 TigerVector 博客内容
    return {
      statusCode: 200,
      data: {
        content: BLOG_CONTENT
      }
    }
  } catch (error) {
    console.error('获取论文内容失败', error)
    // 确保返回适当的响应格式，而不是抛出错误
    return {
      statusCode: 500,
      error: '获取论文内容失败'
    }
  }
} 